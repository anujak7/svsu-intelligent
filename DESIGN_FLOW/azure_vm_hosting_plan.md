# ☁️ Azure VM Hosting Guide - SVSU Intelligent

This guide explains how to correctly host and access the SVSU Intelligent chatbot on an Azure VM.

## 1. Running the Application

The application is configured to run on port **8501** and listen on all interfaces. Use the following command on your VM:

```bash
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

> [!IMPORTANT]
> Ensure you have activated your virtual environment (`.venv\Scripts\activate`) before running the command.

## 2. Opening the Firewall (Azure Portal)

By default, Azure VMs block all incoming traffic except for SSH/RDP. You **must** open port 8501 to access the chatbot:

1.  Go to the **Azure Portal**.
2.  Navigate to your **Virtual Machine** and select **Networking** (or **Network Security Group**).
3.  Click **Add inbound port rule**.
4.  Set the following values:
    - **Destination port ranges**: `8501`
    - **Protocol**: `TCP`
    - **Action**: `Allow`
    - **Priority**: `300` (any available priority)
    - **Name**: `AllowStreamlit8501`
5.  Click **Add**.

## 3. Accessing the Chatbot

Once the app is running and the port is open, access it via your browser using the Public IP and the port number:

**URL:** `http://98.70.37.219:8501`

## 4. Troubleshooting `ERR_CONNECTION_REFUSED`

If you still see this error:
- **Port specification**: Ensure you added `:8501` to the IP. Double-check if you're using `http` and not `https` unless you have SSL configured.
- **Service Status**: Check if the command in step 1 is still running. If it crashed, check `error.log`.
- **Local Firewall**: Ensure the Windows/Linux firewall *inside* the VM is also allowing port 8501.
    ```bash
    # Windows (PowerShell)
    New-NetFirewallRule -DisplayName "Allow Port 8501" -Direction Inbound -LocalPort 8501 -Protocol TCP -Action Allow
    ```
