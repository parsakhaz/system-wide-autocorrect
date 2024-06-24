import logging
import sys
import time
from typing import Optional, List
from pynput import keyboard
from symspellpy import SymSpell, Verbosity
import pkg_resources
from transformers import AutoTokenizer, AutoModelForMaskedLM
import torch

class Autocorrector:
    def __init__(self, dictionary_path: Optional[str] = None, max_edit_distance: int = 2):
        self.sym_spell = SymSpell(max_dictionary_edit_distance=max_edit_distance, prefix_length=7)
        self.keyboard_controller = keyboard.Controller()
        self.current_word = ""
        self.ctrl_pressed = False
        self.load_dictionary(dictionary_path)
        self.never_correct = set(['I', 'a', 'A', 'the', 'The', 'an', 'An', 'and', 'And', 'in', 'In', 'on', 'On', 'at', 'At', 'is', 'Is', 'it', 'It', 'tbh', 'TBH'])
        
        # Initialize the language model and tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
        self.model = AutoModelForMaskedLM.from_pretrained("distilbert-base-uncased")
        self.model.eval()  # Set the model to evaluation mode
        
        # Initialize context window
        self.context_window = ""
        self.max_context_length = 100  # Increased for better context

    def load_dictionary(self, dictionary_path: Optional[str] = None):
        if dictionary_path is None:
            dictionary_path = pkg_resources.resource_filename("symspellpy", "frequency_dictionary_en_82_765.txt")
        if not self.sym_spell.load_dictionary(dictionary_path, term_index=0, count_index=1):
            logging.error(f"Failed to load dictionary from {dictionary_path}")
            sys.exit(1)
        logging.info(f"Dictionary loaded from {dictionary_path}")

    def on_press(self, key: keyboard.Key) -> bool:
        try:
            if key == keyboard.Key.home:
                logging.info("Killswitch activated. Exiting...")
                return False  # This stops the listener

            if hasattr(key, 'char') and key.char is not None and key.char.isalnum():
                self.current_word += key.char
                logging.debug(f"Current word: {self.current_word}")
            elif key == keyboard.Key.space:
                self.handle_space()
            elif key == keyboard.Key.backspace:
                self.handle_backspace()
            elif key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                self.ctrl_pressed = True
            elif self.ctrl_pressed and key == keyboard.Key.backspace:
                self.handle_ctrl_backspace()
            elif key in [keyboard.Key.enter, keyboard.Key.tab]:
                self.handle_word_completion()
            elif hasattr(key, 'char') and key.char in ['.', '!', '?']:
                self.handle_sentence_end(key.char)

        except Exception as e:
            logging.error(f"Error in on_press: {e}", exc_info=True)

        return True

    def on_release(self, key: keyboard.Key) -> bool:
        if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
            self.ctrl_pressed = False
        return True

    def handle_space(self):
        logging.info("Space detected")
        if self.current_word:
            context = self.get_current_context()
            corrected_word = self.correct_word(self.current_word, context)
            if corrected_word != self.current_word:
                self.apply_correction(corrected_word)
            self.update_context(corrected_word)
            self.current_word = ""

    def handle_backspace(self):
        if self.current_word:
            self.current_word = self.current_word[:-1]
        else:
            # Remove the last character from the context
            self.context_window = self.context_window[:-1]
        logging.debug(f"Backspace pressed. Current word: {self.current_word}")
        logging.debug(f"Updated context: {self.context_window}")

    def handle_ctrl_backspace(self):
        logging.info("CTRL + Backspace detected")
        # Remove the last word from the context
        context_words = self.get_current_context().split()
        if context_words:
            context_words.pop()
        self.context_window = ' '.join(context_words)
        self.current_word = ""
        logging.debug(f"Updated context after CTRL+Backspace: {self.context_window}")

    def handle_word_completion(self):
        if self.current_word:
            context = self.get_current_context()
            corrected_word = self.correct_word(self.current_word, context)
            if corrected_word != self.current_word:
                self.apply_correction(corrected_word)
            self.update_context(corrected_word)
            self.current_word = ""

    def handle_sentence_end(self, punctuation: str):
        if self.current_word:
            context = self.get_current_context()
            corrected_word = self.correct_word(self.current_word, context)
            if corrected_word != self.current_word:
                self.apply_correction(corrected_word)
            self.update_context(corrected_word + punctuation)
            self.current_word = ""

    def update_context(self, word: str):
        self.context_window += f" {word}"
        words = self.context_window.split()
        self.context_window = ' '.join(words[-self.max_context_length:])
        logging.debug(f"Updated context window: {self.context_window}")

    def get_current_context(self) -> str:
        return self.context_window

    def correct_word(self, word: str, context: str) -> str:
        if word.lower() in self.never_correct or len(word) <= 2:
            logging.info(f"Word '{word}' is in never_correct list or too short. Skipping correction.")
            return word
        try:
            start_time = time.time()
            suggestions = self.sym_spell.lookup(word.lower(), Verbosity.CLOSEST, max_edit_distance=2, include_unknown=True)
            
            logging.debug(f"Context for correction: '{context}'")
            logging.debug(f"Word to correct: '{word}'")
            logging.debug(f"Suggestions from SymSpell: {[(s.term, s.distance) for s in suggestions]}")
            
            if suggestions:
                # Use context model to re-rank suggestions
                ranked_suggestions = self.rerank_suggestions(context, [s.term for s in suggestions])
                
                logging.debug(f"Ranked suggestions after reranking: {ranked_suggestions}")
                
                if ranked_suggestions:
                    suggestion = ranked_suggestions[0]
                    end_time = time.time()
                    latency = end_time - start_time
                    logging.info(f"Correction process for '{word}':")
                    logging.info(f"  Original word: '{word}'")
                    logging.info(f"  Corrected to: '{suggestion}'")
                    logging.info(f"  Correction time: {latency:.6f} seconds")
                    logging.info(f"  Context used: '{context}'")
                    
                    # Preserve original capitalization
                    if word.istitle():
                        suggestion = suggestion.capitalize()
                    elif word.isupper():
                        suggestion = suggestion.upper()
                    
                    return suggestion
                else:
                    logging.warning(f"No valid suggestions after reranking for '{word}'")
            else:
                logging.debug(f"No suggestions from SymSpell for '{word}'")
        except Exception as e:
            logging.error(f"Error in correct_word: {e}", exc_info=True)
        return word

    def rerank_suggestions(self, context: str, suggestions: List[str]) -> List[str]:
        if not suggestions:
            logging.warning("No suggestions provided for reranking")
            return []

        # Create context with mask token at the end
        context_with_mask = f"{context} {self.tokenizer.mask_token}"

        inputs = self.tokenizer(context_with_mask, return_tensors="pt", truncation=True, max_length=512)
        mask_token_index = torch.where(inputs["input_ids"] == self.tokenizer.mask_token_id)[1]

        if mask_token_index.numel() == 0:
            logging.warning("No mask token found in the input")
            return suggestions

        with torch.no_grad():
            outputs = self.model(**inputs)
        
        logits = outputs.logits
        mask_token_logits = logits[0, mask_token_index, :]
        
        # Get the token IDs for the suggestions
        suggestion_token_ids = self.tokenizer.convert_tokens_to_ids(suggestions)
        
        # Get the logits for the suggestion tokens
        suggestion_logits = mask_token_logits[:, suggestion_token_ids]
        
        # Calculate probabilities
        probabilities = torch.nn.functional.softmax(suggestion_logits, dim=-1)
        
        # Sort suggestions based on their probabilities
        sorted_indices = torch.argsort(probabilities, descending=True)
        
        if sorted_indices.numel() == 0:
            logging.warning("No valid indices after sorting suggestions")
            return suggestions

        reranked_suggestions = [suggestions[i] for i in sorted_indices[0]]
        
        # Log the reranking process
        logging.debug("Reranking process:")
        logging.debug(f"Context: '{context}'")
        logging.debug(f"Context with mask: '{context_with_mask}'")
        logging.debug(f"Original suggestions: {suggestions}")
        logging.debug(f"Reranked suggestions: {reranked_suggestions}")
        logging.debug("Probabilities for each suggestion:")
        for suggestion, prob in zip(suggestions, probabilities[0].tolist()):
            logging.debug(f"  {suggestion}: {prob:.4f}")
        
        return reranked_suggestions

    def apply_correction(self, corrected_word: str):
        logging.info(f"Applying correction: '{self.current_word}' to '{corrected_word}'")
        for _ in range(len(self.current_word) + 1):  # Add one more backspace
            self.keyboard_controller.press(keyboard.Key.backspace)
            self.keyboard_controller.release(keyboard.Key.backspace)
        self.keyboard_controller.type(corrected_word + " ")
        # Provide visual feedback
        self.keyboard_controller.press(keyboard.Key.left)
        self.keyboard_controller.release(keyboard.Key.left)
        self.keyboard_controller.press(keyboard.Key.right)
        self.keyboard_controller.release(keyboard.Key.right)

def main():
    logging.basicConfig(filename='autocorrect.log', level=logging.DEBUG, 
                        format='%(asctime)s - %(levelname)s - %(message)s')
    
    autocorrector = Autocorrector()
    
    with keyboard.Listener(on_press=autocorrector.on_press, on_release=autocorrector.on_release) as listener:
        listener.join()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Script terminated by user")
    except Exception as e:
        logging.error(f"Unhandled exception: {e}", exc_info=True)