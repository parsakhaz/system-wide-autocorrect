# System-Wide Autocorrect

This project provides a system-wide autocorrect feature using the `symspellpy` library and the `pynput` library to listen to keyboard events.

## Prerequisites

### Python Environment

Ensure you have Python 3.6 or later installed. You can download it from [python.org](https://www.python.org/downloads/).

### Microsoft Visual C++ Build Tools

The `symspellpy` package requires `editdistpy`, which needs Microsoft Visual C++ 14.0 or greater to build. Follow these steps to install the required build tools:

1. Visit the [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) page.
2. Download and install the build tools.
3. During installation, ensure you select the "Desktop development with C++" workload.

After installation, you can verify that the tools are installed correctly by running the following command in your terminal:

```sh
cl
```

This should display the version of the Microsoft C++ compiler.

## Installation

1. **Clone the repository:**

   ```sh
   git clone https://github.com/yourusername/system-wide-autocorrect.git
   cd system-wide-autocorrect
   ```

2. **Create a virtual environment:**

   ```sh
   python -m venv .venv
   ```

3. **Activate the virtual environment:**
   - On Windows:

     ```sh
     .venv\Scripts\activate
     ```

   - On macOS and Linux:

     ```sh
     source .venv/bin/activate
     ```

4. **Install the required packages:**

   ```sh
   pip install -r requirements.txt
   ```

## Usage

Run the `autocorrect.py` script to start the system-wide autocorrect feature:

```sh
python autocorrect.py
```

Press the `Home` key to stop the listener and exit the program.

## Logging

Logs are written to `autocorrect.log` in the project directory. This file contains information about key events and any errors that occur during execution.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

Make sure to replace `https://github.com/yourusername/system-wide-autocorrect.git` with the actual URL of your repository. Additionally, create a `requirements.txt` file with the necessary dependencies:

```plaintext
pynput
symspellpy
```
