# ImaginationPlanet Automation

## Overview

ImaginationPlanet Automation is a Python-based tool designed to automate specific tasks within the ImaginationPlanet application. This script facilitates routine operations, enhancing efficiency and user experience.

## Prerequisites

Before running the script, ensure your environment meets the following requirements:

- **Python Version:** Python 3.11

- **Virtual Environment:** It's recommended to use a virtual environment to manage dependencies.

  ```bash
  python3.11 -m venv myenv
  source myenv/bin/activate
  ```

- **Dependencies:** Install the necessary packages using `pip`:

  ```bash
  pip install opencv-python numpy pyautogui
  ```

  *Note:* The `pyobjc-framework-Quartz` package is specific to macOS systems. If you're using a different operating system, please refer to the relevant documentation for equivalent packages.

## Usage

The script offers two primary modes of operation:

1. **Regular Run:** Executes a full sequence, including grabbing the cat and engaging in fights until all tickets are utilized.

   ```bash
   python imaginationplanet.py -r=True
   ```

2. **Fight Only:** Initiates only the fighting sequence.

   ```bash
   python imaginationplanet.py -f=True
   ```

## Command-Line Arguments

- `-r` or `--run`: Set to `True` to perform a regular run. Default is `False`.

- `-f` or `--fight`: Set to `True` to initiate the fight sequence. Default is `False`.

*Note:* Ensure that only one of the above options is set to `True` at a time to avoid conflicts.

## Setup Instructions

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/jxue/ImaginationPlanetAutomation.git
   cd ImaginationPlanetAutomation
   ```

2. **Activate Virtual Environment:**

   ```bash
   source myenv/bin/activate
   ```

3. **Install Dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Script:**

   Choose the desired mode of operation as described in the [Usage](#usage) section.

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository.

2. Create a new branch:

   ```bash
   git checkout -b feature/YourFeatureName
   ```

3. Commit your changes:

   ```bash
   git commit -m 'Add some feature'
   ```

4. Push to the branch:

   ```bash
   git push origin feature/YourFeatureName
   ```

5. Open a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [OpenCV](https://opencv.org/)
- [NumPy](https://numpy.org/)
- [PyAutoGUI](https://pyautogui.readthedocs.io/)
