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

### Run the Proxy
The proxy can be run from Python like so:
```sh

HTTP
python3 /opt/prism-vnc-proxy/prism_vnc_proxy.py --prism_hostname=1.2.3.4 --prism_username=PC_USERNAME --prism_password=PC_PASSWORD --bind_port=8080 --use_pc'

HTTPS
sudo -E /opt/prism-vnc-proxy/.venv/bin/python3 prism_vnc_proxy.py --prism_hostname=1.2.3.4 --prism_username=PC_USERNAME --prism_password=PC_PASSWORD --ssl_cert=/opt/prism-vnc-proxy/certs/fullchain.pem --ssl_key=/opt/prism-vnc-proxy/certs/privkey.pem --bind_port=443 --use_pc

```

### Command-line Options
- `--bind_address`: Address to bind the HTTP server to (default: "").
- `--bind_port`: Port to bind the HTTP server to (default: 8080).
- `--prism_hostname`: Hostname of the Prism gateway.
- `--prism_username`: Username for the Prism gateway (default: "admin").
- `--prism_password`: Password for the Prism gateway.

###
- `vncproxy.service (/etc/systemd/system/vncproxy.service)
- [Unit]
- Description=Prism VNC Proxy
- After=network.target
- 
- [Service]
- Type=simple
- User=nutanix
- WorkingDirectory=/opt/prism-vnc-proxy
- ExecStart=/opt/prism-vnc-proxy/.venv/bin/python3 prism_vnc_proxy.py \
-   --prism_hostname=1.2.3.4.5 \
-   --prism_username=PC_USERNAME
-   --prism_password=PC_PASSWORD \
-   --ssl_cert=/opt/prism-vnc-proxy/certs/fullchain.pem \
-   --ssl_key=/opt/prism-vnc-proxy/certs/privkey.pem \
-   --bind_port=443 \
-   --use_pc
- Environment=VIRTUAL_ENV=/opt/prism-vnc-proxy/.venv
- Environment=PATH=/opt/prism-vnc-proxy/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
- Restart=always
- User=root
- 
- [Install]
- WantedBy=multi-user.target

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
$ sudo netstat -an | grep 8098
tcp        0      0 0.0.0.0:8098            0.0.0.0:*               LISTEN
```

### Access Resources
Access the VNC UI via the following URL scheme:
```
http://<proxy-host>:<bind_port>/console/vnc_auto.html?path=proxy/<vm_uuid>&name=<vm_name>
```

## Development

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
