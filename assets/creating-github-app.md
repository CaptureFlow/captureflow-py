# Creating a GitHub App for CaptureFlow

This guide provides step-by-step instructions for creating a GitHub App necessary for CaptureFlow, enabling the automation of improvement merge requests (MRs). You'll learn how to retrieve your `APP_ID` and `PRIVATE_KEY`, which are essential for configuring the CaptureFlow server-side component.

## Step 1: Create a New GitHub App

1. Navigate to your GitHub account settings.
2. In the left sidebar, click on **Developer settings**.
3. Select **GitHub Apps** and then click on the **New GitHub App** button.
4. Fill in the necessary details:
   - **GitHub App name**: Provide a unique name for your app.
   - **Homepage URL**: You can use the URL of your project or repository.
   - **Webhook**: Disable it, as it's not required for CaptureFlow.
   - **Repository permissions**: Set the permissions required by CaptureFlow, typically including:
     - **Contents**: `Read & write` for accessing and modifying code.
     - **Pull requests**: `Read & write` for creating and managing pull requests.
5. Scroll down and click on **Create GitHub App**.

## Step 2: Generate a Private Key

After creating your GitHub App, you'll be redirected to the app's settings page.

1. Scroll down to the **Private keys** section.
2. Click on **Generate a private key**.
3. Once the key is generated, it will be automatically downloaded to your computer. This file contains your `PRIVATE_KEY`.

## Step 3: Retrieve Your App ID

1. On the same GitHub App settings page, find the **App ID** section at the top.
2. Note down the `App ID` displayed here. This is your `APP_ID`.

## Configuring CaptureFlow

With your `APP_ID` and `PRIVATE_KEY` obtained, you're ready to configure the CaptureFlow server-side component. You need to set corresponding environment variables defined in [config.py](https://github.com/CaptureFlow/captureflow-py/blob/main/serverside/src/config.py).

Yes, also, please base64 encode your private key :)
