# Prism VNC Proxy

This project provides a small HTTP proxy and frontend for VM VNC WebSockets. It uses `aiohttp` to run an HTTP server that proxies WebSocket traffic through a Prism gateway and provides a frontend UI for Acropolis VM VNC WebSockets.

## Features
- Proxies WebSocket traffic to the VNC server for specified VM UUIDs.
- Provides a frontend UI for VNC WebSockets, using noNVC to connect to `aiohttp`
- Handles authentication with Prism and establishes WebSocket connections between clients and the Prism server.
- Serves static content, which is noVNC and jquery.

## Setup Python Environment

### Preparing the Environment
This project will only execute within a python virtual environment (venv), which helps ensure that you're operating in a clean Python environment and do not have conflicts with system-installed Python packages.

Reference: [Python Packaging User Guide](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/)

### Setup Virtual Environment
```sh
python3 -m venv .venv
source .venv/bin/activate
```

### Install Project Requirements
```sh
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

## Usage

### Environment Configuration
The project supports using a `.env` file for configuration. This is the recommended approach for managing sensitive credentials and configuration settings.

1. Copy the example environment file to create your own configuration:
   ```sh
   cp .env.example .env
   ```

2. Edit the `.env` file with your specific configuration:
   ```sh
   # Prism VNC Proxy Configuration
   PRISM_HOSTNAME=your.prism.hostname.or.ip
   PRISM_USERNAME=admin
   PRISM_PASSWORD=your_secure_password
   BIND_PORT=443

   # SSL Configuration
   SSL_CERT=/opt/prism-vnc-proxy/certs/fullchain.pem
   SSL_KEY=/opt/prism-vnc-proxy/certs/privkey.pem
   ```

3. Secure your `.env` file with appropriate permissions:
   ```sh
   chmod 600 .env
   ```

> **Note**: The `.env` file contains sensitive information and is excluded from version control via `.gitignore`. Never commit your actual `.env` file to the repository.

### Environment Configuration
The project supports using a `.env` file for configuration. This is the recommended approach for managing sensitive credentials and configuration settings.

1. Copy the example environment file to create your own configuration:
   ```sh
   cp .env.example .env
   ```

2. Edit the `.env` file with your specific configuration:
   ```sh
   # Prism VNC Proxy Configuration
   PRISM_HOSTNAME=your.prism.hostname.or.ip
   PRISM_USERNAME=admin
   PRISM_PASSWORD=your_secure_password
   BIND_PORT=443

   # SSL Configuration
   SSL_CERT=/opt/prism-vnc-proxy/certs/fullchain.pem
   SSL_KEY=/opt/prism-vnc-proxy/certs/privkey.pem
   ```

3. Secure your `.env` file with appropriate permissions:
   ```sh
   chmod 600 .env
   ```

> **Note**: The `.env` file contains sensitive information and is excluded from version control via `.gitignore`. Never commit your actual `.env` file to the repository.

### Run the Proxy
The proxy can be run from Python like so:

#### Using Command Line Arguments

HTTP
```sh
python3 /opt/prism-vnc-proxy/prism_vnc_proxy.py --prism_hostname=YOUR_PRISM_HOSTNAME --prism_username=YOUR_PRISM_USERNAME --prism_password=YOUR_PRISM_PASSWORD --bind_port=8080 --use_pc
```
HTTPS
```sh
sudo env VIRTUAL_ENV=/opt/prism-vnc-proxy/.venv /opt/prism-vnc-proxy/.venv/bin/python3 /opt/prism-vnc-proxy/prism_vnc_proxy.py --prism_hostname=YOUR_PRISM_HOSTNAME --prism_username=YOUR_PRISM_USERNAME --prism_password=YOUR_PRISM_PASSWORD --bind_port=443 --ssl_cert=/opt/prism-vnc-proxy/certs/fullchain.pem --ssl_key=/opt/prism-vnc-proxy/certs/privkey.pem --use_pc
```

### Command-line Options
- `--bind_address`: Address to bind the HTTP server to (default: "").
- `--bind_port`: Port to bind the HTTP server to (default: 8080).
- `--prism_hostname`: Hostname of the Prism gateway.
- `--prism_username`: Username for the Prism gateway (default: "admin").
- `--prism_password`: Password for the Prism gateway.

### VNC Proxy Service
/etc/systemd/system/vncproxy.service

#### Option 1: Using Command Line Arguments

```sh
[Unit]
Description=Prism VNC Proxy
After=network.target

[Service]
Type=simple
User=nutanix
WorkingDirectory=/opt/prism-vnc-proxy
ExecStart=/opt/prism-vnc-proxy/.venv/bin/python3 prism_vnc_proxy.py \
  --prism_hostname=YOUR_PRISM_HOSTNAME \
  --prism_username=YOUR_PRISM_USERNAME \
  --prism_password=YOUR_PRISM_PASSWORD \
  --ssl_cert=/opt/prism-vnc-proxy/certs/fullchain.pem \
  --ssl_key=/opt/prism-vnc-proxy/certs/privkey.pem \
  --bind_port=443 \
  --use_pc
Environment=VIRTUAL_ENV=/opt/prism-vnc-proxy/.venv
Restart=always
User=root
# Root is required to bind to privileged port 443
# Remove ssl_cert & ssl_key for http & change bind_port
# Remove use_pc for Prism Element

[Install]
WantedBy=multi-user.target
```

#### Option 2: Using Environment File (Recommended)

For better security and easier configuration management, you can modify the service to use the `.env` file:

```sh
[Unit]
Description=Prism VNC Proxy
After=network.target
```

#### Option 2: Using Environment File (Recommended)

For better security and easier configuration management, you can modify the service to use the `.env` file:

```sh
[Unit]
Description=Prism VNC Proxy
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/prism-vnc-proxy
ExecStart=/opt/prism-vnc-proxy/.venv/bin/python3 prism_vnc_proxy.py \
  --prism_hostname=${PRISM_HOSTNAME} \
  --prism_username=${PRISM_USERNAME} \
  --prism_password=${PRISM_PASSWORD} \
  --ssl_cert=${SSL_CERT} \
  --ssl_key=${SSL_KEY} \
  --bind_port=${BIND_PORT} \
  --use_pc
Environment=VIRTUAL_ENV=/opt/prism-vnc-proxy/.venv
EnvironmentFile=/opt/prism-vnc-proxy/.env
Restart=always
User=root
# Root is required to bind to privileged port 443

[Install]
WantedBy=multi-user.target
```

> **Note**: Make sure the `.env` file has restricted permissions (chmod 600) and is owned by the appropriate user.

### Endpoints
- `/proxy/$vm_uuid`: Proxies WebSocket traffic to the VNC server for the specified VM UUID.
- `/console/vnc_auto.html?path=proxy/$vm_uuid&name=$name`: Provides a frontend UI for the VNC WebSocket.

## Validate Proxy is Running
You can check if the proxy is running (crudely) with `netstat` like so:
```sh
sudo netstat -an | grep <bind_port>
```
Example:
```sh
$ sudo netstat -an | grep 8080
tcp        0      0 0.0.0.0:8080            0.0.0.0:*               LISTEN
```

### Access Resources
Access the VNC UI via the following URL scheme:
```
http://<proxy-host>:<bind_port>/console/vnc_auto.html?path=proxy/<vm_uuid>&name=<vm_name>
```

## Development

### Environment Variables and Security Notes

#### Using Environment Variables with systemd
When using the systemd service with the EnvironmentFile directive, the environment variables from the `.env` file will be automatically available to your application through the systemd service.

The systemd service will read the variables from the `.env` file and pass them to your application as environment variables, which can then be accessed in the command line arguments of your application.

This approach doesn't require any code changes to your Python application, as it continues to use command-line arguments.

#### Security Best Practices for .env Files

1. **File Permissions**:
   - Always set restrictive permissions on your .env file: `chmod 600 .env`
   - This ensures only the file owner can read or write to it

2. **Ownership**:
   - When running as a service, ensure the .env file is owned by the appropriate user:
     ```sh
     sudo chown root:root .env  # If running service as root
     # OR
     sudo chown nutanix:nutanix .env  # If running service as nutanix
     ```

3. **Credential Management**:
   - Regularly rotate passwords and update the .env file
   - Use strong, unique passwords for Prism credentials
   - Consider using a secrets management solution for production environments

4. **Backup Considerations**:
   - If backing up the .env file, ensure backups are also secured
   - Consider encrypting backups that contain the .env file

5. **Deployment**:
   - Never commit the actual .env file to version control
   - Use the provided .env.example as a template
   - Document the process for securely transferring the .env file to new deployments

6. **Monitoring**:
   - Regularly audit who has access to the .env file
   - Consider logging access attempts to the directory containing sensitive files

### Logging
Logs information and errors to the console using the `logging` module.

### Troubleshooting
If you encounter issues while running the proxy, consider the following steps:

1. **Check Logs**: 
   - Review the console logs for any error messages or warnings
   - For systemd services, use `journalctl -u vncproxy.service`

2. **Validate Configuration**: 
   - Ensure that the command-line options are correctly specified
   - Verify the .env file contains all required variables
   - Check for typos or formatting issues in the .env file

3. **Environment Variable Issues**:
   - Verify the systemd service can access the .env file:
     ```sh
     sudo systemctl show vncproxy.service -p EnvironmentFile
     ```
   - Test environment variable expansion:
     ```sh
     sudo systemctl show vncproxy.service -p Environment
     ```
   - Check file permissions and ownership of the .env file

4. **Network Issues**: 
   - Verify network connectivity between the proxy server and the Prism gateway
   - Test basic connectivity: `ping <PRISM_HOSTNAME>`
   - Test port connectivity: `nc -zv <PRISM_HOSTNAME> 443`

5. **SSL Certificate Issues**:
   - Verify SSL certificate and key paths are correct
   - Check certificate validity: `openssl x509 -in <SSL_CERT> -text -noout`
   - Ensure certificate and key match: `diff <(openssl x509 -in <SSL_CERT> -pubkey -noout) <(openssl pkey -in <SSL_KEY> -pubout)`

6. **Dependencies**: 
   - Ensure all required Python packages are installed and up-to-date
   - Verify virtual environment is activated when installing or running
[Service]
Type=simple
WorkingDirectory=/opt/prism-vnc-proxy
ExecStart=/opt/prism-vnc-proxy/.venv/bin/python3 prism_vnc_proxy.py \
  --prism_hostname=${PRISM_HOSTNAME} \
  --prism_username=${PRISM_USERNAME} \
  --prism_password=${PRISM_PASSWORD} \
  --ssl_cert=${SSL_CERT} \
  --ssl_key=${SSL_KEY} \
  --bind_port=${BIND_PORT} \
  --use_pc
Environment=VIRTUAL_ENV=/opt/prism-vnc-proxy/.venv
EnvironmentFile=/opt/prism-vnc-proxy/.env
Restart=always
User=root
# Root is required to bind to privileged port 443

[Install]
WantedBy=multi-user.target
```

> **Note**: Make sure the `.env` file has restricted permissions (chmod 600) and is owned by the appropriate user.

### Endpoints
- `/proxy/$vm_uuid`: Proxies WebSocket traffic to the VNC server for the specified VM UUID.
- `/console/vnc_auto.html?path=proxy/$vm_uuid&name=$name`: Provides a frontend UI for the VNC WebSocket.

## Validate Proxy is Running
You can check if the proxy is running (crudely) with `netstat` like so:
```sh
sudo netstat -an | grep <bind_port>
```
Example:
```sh
$ sudo netstat -an | grep 8080
tcp        0      0 0.0.0.0:8080            0.0.0.0:*               LISTEN
```

### Access Resources
Access the VNC UI via the following URL scheme:
```
http://<proxy-host>:<bind_port>/console/vnc_auto.html?path=proxy/<vm_uuid>&name=<vm_name>
```

## Development

### Using Environment Variables with systemd
When using the systemd service with the EnvironmentFile directive, the environment variables from the `.env` file will be automatically available to your application through the systemd service.

The systemd service will read the variables from the `.env` file and pass them to your application as environment variables, which can then be accessed in the command line arguments of your application.

This approach doesn't require any code changes to your Python application, as it continues to use command-line arguments.

### Logging
Logs information and errors to the console using the `logging` module.

### Troubleshooting
If you encounter issues while running the proxy, consider the following steps:
1. **Check Logs**: Review the console logs for any error messages or warnings.
2. **Validate Configuration**: Ensure that the command-line options are correctly specified.
3. **Network Issues**: Verify network connectivity between the proxy server and the Prism gateway.
4. **Dependencies**: Ensure all required Python packages are installed and up-to-date.

### File Structure
- `prism_vnc_proxy.py`: Main entry point for the VNC proxy server.
- `wsgi_prism_websocket_proxy.py`: Handles WebSocket proxying to the Prism gateway.
- `wsgi_file_handler.py`: Asynchronous file handler for serving static files.
- `wsgi_http_handler.py`: Asynchronous HTTP handler that adapts a WSGI application to be used with `aiohttp`.

## Contributing
We welcome contributions to improve the Prism VNC Proxy. Please follow these guidelines:
1. Fork the repository and create a new branch for your feature or bugfix.
2. Write clear, concise commit messages.
3. Ensure your code adheres to the project's coding standards.
4. Submit a pull request with a detailed description of your changes.

For more detailed information, please refer to the source code and comments within the files.
