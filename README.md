# Flask File Server 🌐

![GitHub release](https://img.shields.io/github/v/release/deepiitain/flask-fileserver?style=flat-square) ![License](https://img.shields.io/github/license/deepiitain/flask-fileserver?style=flat-square)

Welcome to the **Flask File Server**! This project provides a simple, internal-use file server that integrates Azure AD authentication and offers per-user bucket-based access control. It's designed to be lightweight and easy to set up, making it ideal for internal tools and file storage needs.

## Table of Contents

- [Features](#features)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Authentication](#authentication)
- [Bucket Management](#bucket-management)
- [Installation](#installation)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## Features

- **Azure AD Authentication**: Secure your files with robust authentication.
- **Per-User Access Control**: Each user can have their own bucket for file storage.
- **Lightweight and Minimal**: Quick to set up and easy to use.
- **Self-Hosted**: Host it on your own server for complete control.
- **File Uploads and Downloads**: Easily manage your files with simple API calls.

## Getting Started

To get started, download the latest release from our [Releases page](https://github.com/deepiitain/flask-fileserver/releases). Follow the instructions to set up the server on your local machine or server.

## Usage

Once set up, you can use the file server to upload, download, and manage files in a user-friendly way. Each user will have access to their own storage bucket, ensuring that files are organized and secure.

## API Endpoints

### File Upload

- **Endpoint**: `/upload`
- **Method**: `POST`
- **Description**: Upload a file to your bucket.

### File Download

- **Endpoint**: `/download/<file_id>`
- **Method**: `GET`
- **Description**: Download a file from your bucket.

### List Files

- **Endpoint**: `/files`
- **Method**: `GET`
- **Description**: List all files in your bucket.

## Authentication

This server uses Azure AD for authentication. Users must log in using their Azure credentials to access their files. The server will handle the authentication process and provide tokens for secure access.

## Bucket Management

Each user has their own bucket for file storage. Buckets are isolated, ensuring that users cannot access each other's files. You can manage buckets through the API, creating and deleting them as needed.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/deepiitain/flask-fileserver.git
   cd flask-fileserver
   ```

2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up your Azure AD credentials in the configuration file.

4. Run the server:
   ```bash
   python app.py
   ```

Visit the server in your web browser to begin using the file server.

## Contributing

We welcome contributions to improve the Flask File Server. If you have suggestions or find issues, please open an issue or submit a pull request. Follow these steps to contribute:

1. Fork the repository.
2. Create a new branch for your feature or fix.
3. Make your changes and commit them.
4. Push your changes to your fork.
5. Submit a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contact

For questions or support, please contact the repository owner. You can reach out via GitHub issues or directly through email.

---

For more information and updates, please check the [Releases section](https://github.com/deepiitain/flask-fileserver/releases). 

Happy file sharing!