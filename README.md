# Telegram Group Sender

[![Python Version](https://img.shields.io/badge/python-3.x-blue.svg)](https://www.python.org/downloads/)

A simple, user-friendly application designed to send messages to multiple Telegram groups efficiently. This tool supports managing multiple Telegram accounts, customizable delays to prevent spam detection, and real-time logging for transparency.

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## Features

- Send messages to all your Telegram groups with a single action.
- Add and manage multiple Telegram accounts seamlessly.
- Configure delays between messages to minimize the risk of being flagged as spam.
- Real-time logging to monitor the sending process and debug issues.

## Requirements

- Python 3.x
- `customtkinter` (for the graphical user interface)
- `telethon` (for interacting with the Telegram API)

## Installation

1. Clone the repository:
   ```bash:disable-run
   git clone https://github.com/user/repo.git
   cd repo
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

   If you encounter issues with dependencies, ensure your Python environment is up to date and consider using a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Unix-based systems
   venv\Scripts\activate     # On Windows
   pip install -r requirements.txt
   ```

## Usage

1. Launch the application:
   ```bash
   python -m src.main
   ```

2. Add a new Telegram account:
   - Click the "Add New Account" button.
   - Provide your API ID, API Hash, and phone number (obtain these from [my.telegram.org](https://my.telegram.org)).

3. Log in to the selected account:
   - You may receive a verification code via Telegram; enter it when prompted.

4. Load and select groups:
   - Once authenticated, your groups will be automatically loaded.

5. Send messages:
   - Enter the message content in the provided field.
   - Set the desired delay (in seconds) between messages.
   - Click "Start Sending" to begin the process.

   Monitor the real-time logs for progress and any errors.

## Configuration

- **API Credentials**: Always keep your API ID and Hash secure. Do not share them publicly.
- **Delay Settings**: Recommended delay is 5-10 seconds per message to comply with Telegram's usage policies.
- **Logging**: Logs are displayed in the application interface. For persistent logging, consider modifying the source code to write to a file.

## Troubleshooting

- **Login Issues**: Ensure your phone number is correctly formatted (e.g., +1234567890). If two-factor authentication is enabled, provide the password when prompted.
- **Group Loading Failures**: Verify your internet connection and Telegram API access. Rate limits may apply; try again after a short wait.
- **Dependency Errors**: If `customtkinter` or `telethon` fail to install, check for compatible Python versions or conflicting packages.
- For other issues, refer to the [Telethon documentation](https://docs.telethon.dev/) or open an issue on the repository.

## Contributing

Contributions are welcome! Please follow these steps:
1. Fork the repository.
2. Create a new branch (`git checkout -b feature/YourFeature`).
3. Commit your changes (`git commit -m 'Add YourFeature'`).
4. Push to the branch (`git push origin feature/YourFeature`).
5. Open a Pull Request.

Ensure your code adheres to PEP 8 standards and includes relevant tests.

```
