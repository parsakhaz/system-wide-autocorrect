import logging
import sys
import time
from typing import Optional
from pynput import keyboard
from symspellpy import SymSpell, Verbosity
import pkg_resources

class Autocorrector:
    def __init__(self, dictionary_path: Optional[str] = None, max_edit_distance: int = 3):
        self.sym_spell = SymSpell(max_dictionary_edit_distance=max_edit_distance, prefix_length=7)
        self.keyboard_controller = keyboard.Controller()
        self.current_word = ""
        self.ctrl_pressed = False
        self.load_dictionary(dictionary_path)
        self.never_correct = set(['I', 'a', 'A', 'the', 'The', 'an', 'An', 'and', 'And', 'in', 'In', 'on', 'On', 'at', 'At', 'is', 'Is', 'it', 'It'])

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
            elif self.ctrl_pressed and key in [keyboard.Key.left, keyboard.Key.right]:
                self.handle_ctrl_arrow()
            elif self.ctrl_pressed and hasattr(key, 'char') and key.char == 'a':
                self.handle_ctrl_a()
            elif self.ctrl_pressed and hasattr(key, 'char') and key.char == 'c':
                self.handle_ctrl_c()
            elif self.ctrl_pressed and hasattr(key, 'char') and key.char == 'v':
                self.handle_ctrl_v()
            elif hasattr(key, 'char') and key.char == '.':
                logging.info("Period key detected")
                # Handle period key if needed

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
            corrected_word = self.correct_word(self.current_word)
            if corrected_word != self.current_word:
                self.apply_correction(corrected_word)
            self.current_word = ""

    def handle_backspace(self):
        if self.current_word:
            self.current_word = self.current_word[:-1]
        logging.debug(f"Backspace pressed. Current word: {self.current_word}")

    def handle_ctrl_backspace(self):
        logging.info("CTRL + Backspace detected")
        self.current_word = ""
        logging.debug("Current word cleared")

    def handle_ctrl_arrow(self):
        logging.info("CTRL + Arrow detected")
        self.current_word = ""
        logging.debug("Current word cleared")

    def handle_ctrl_a(self):
        logging.info("CTRL + A detected")
        self.current_word = ""
        logging.debug("Current word cleared")

    def handle_ctrl_c(self):
        logging.info("CTRL + C detected")
        self.current_word = ""
        logging.debug("Current word cleared")

    def handle_ctrl_v(self):
        logging.info("CTRL + V detected")
        self.current_word = ""
        logging.debug("Current word cleared")

    def correct_word(self, word: str) -> str:
        if word in self.never_correct:
            return word
        try:
            start_time = time.time()
            suggestions = self.sym_spell.lookup(word.lower(), Verbosity.CLOSEST, max_edit_distance=2)
            end_time = time.time()
            latency = end_time - start_time
            logging.debug(f"Suggestions for '{word}': {[(s.term, s.distance) for s in suggestions]}")
            logging.info(f"Lookup time for '{word}': {latency:.6f} seconds")
            if suggestions:
                corrected = suggestions[0].term
                # Preserve original capitalization
                if word[0].isupper():
                    corrected = corrected.capitalize()
                return corrected
        except Exception as e:
            logging.error(f"Error in correct_word: {e}", exc_info=True)
        return word

    def apply_correction(self, corrected_word: str):
        logging.info(f"Correcting '{self.current_word}' to '{corrected_word}'")
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