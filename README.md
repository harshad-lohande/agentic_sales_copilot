# **🤖 Agentic Sales Co-Pilot**

An autonomous, multi-agent system designed to automate sales email outreach, intelligently process replies, and provide a human-in-the-loop interface for sales representatives via Slack.

## **🚀 Core Features (Current Version)**

* **Autonomous Email Campaign Creation:** A Sales\_Manager agent orchestrates a team of specialized agents to generate multiple email drafts, select the best one, and create a personalized subject line.  
* **Personalized Bulk Emailing:** Sends personalized emails to a list of prospects from a .csv file, using placeholders for both the subject and body.  
* **Intelligent Reply Processing:** Automatically receives email replies via a SendGrid webhook. A dedicated SDR\_Agent then analyzes the reply's content to classify its intent and summarize its key points.  
* **Interactive Human-in-the-Loop (HITL) Interface:** The agent's analysis is sent as an interactive notification to a Slack channel, allowing a human user to take action.  
* **One-Click Actions:** From Slack, a user can:  
  * **Approve & Send:** Immediately send the AI-drafted reply.  
  * **Edit & Send:** Open a pop-up modal to edit the draft before sending.  
  * **Discard:** Mark the reply as handled without taking further action.  
* **Secure & Configurable:** Manages all secret keys and configuration safely through environment variables.

## **Diagram: System Architecture**

This diagram illustrates the complete, end-to-end workflow of the application, from outbound campaign to inbound reply processing.

graph TD  
    subgraph Outbound Campaign  
        A\[1. Run \`main.py\`\] \--\> B{Sales\_Manager Agent};  
        B \--\> C\[Generates & Selects Email\];  
        B \--\> D{Campaign\_Sender Agent};  
        D \--\> E\[Tool: \_send\_personalized\_bulk\_email\_logic\];  
        E \--\> F((SendGrid API));  
        F \--\> G(\[Prospect's Inbox\]);  
    end

    subgraph Inbound Reply  
        G \-- Reply \--\> H((SendGrid Inbound Parse));  
        H \-- Webhook \--\> I\[2. Webhook Server\];  
        I \--\> J{SDR\_Agent};  
        J \--\> K\[Analyzes Reply & Drafts Response\];  
        K \--\> L\[Tool: send\_slack\_notification\];  
        L \--\> M((Slack API));  
        M \--\> N\[📱 Slack Channel Notification\];  
    end

    subgraph Human-in-the-Loop  
        N \-- Button Click \--\> O\[3. Slack Action Handler\];  
        O \-- Approve/Edit \--\> P\[Tool: send\_single\_email\];  
        P \--\> F;  
    end

    style A fill:\#cde4ff  
    style I fill:\#cde4ff  
    style O fill:\#cde4ff

## **🛠️ Tech Stack & Key Libraries**

* **Agent Framework:** agents (OpenAI Agents SDK)  
* **Language:** Python 3.12+  
* **Package Management:** Poetry  
* **Web Framework:** FastAPI (for webhook server)  
* **Email Service (Outbound & Inbound):** SendGrid  
* **User Interface:** Slack SDK (for interactive notifications & modals)  
* **Local Tunneling (Development):** ngrok

## **⚙️ Setup and Installation**

Follow these steps to set up the project locally.

### **1\. Clone the Repository**

git clone \<your-repository-url\>  
cd \<your-repository-name\>

### **2\. Install Dependencies**

This project uses Poetry for dependency management. Ensure you have Poetry installed, then run:

poetry install

### **3\. Configure Environment Variables**

Create a file named .env in the root of the project directory. This file stores all your secret keys and configuration.

\# .env

\# \--- API Keys \---  
OPENAI\_API\_KEY="sk-..."  
SENDGRID\_API\_KEY="SG. ..."  
SLACK\_BOT\_TOKEN="xoxb-..."

\# \--- Configuration \---  
SLACK\_CHANNEL\_ID="C0..." \# The ID of the Slack channel for notifications

### **4\. Set Up External Services**

* **SendGrid:**  
  1. Create an API Key with full access to Mail Send.  
  2. Verify a "Single Sender" email address (e.g., business@yourdomain.com).  
  3. Set up **Inbound Parse** on a subdomain (e.g., replies.yourdomain.com) and point its Destination URL to your ngrok forwarding URL.  
  4. Add the provided MX record (mx.sendgrid.net) to your domain's DNS settings for that subdomain.  
* **Slack:**  
  1. Create a new Slack App named "SDR Agent Notifier".  
  2. Add the chat:write and commands Bot Token Scopes under "OAuth & Permissions".  
  3. Install the app to your workspace and copy the Bot User OAuth Token.  
  4. Enable "Interactivity & Shortcuts" and set the Request URL to your ngrok forwarding URL.  
  5. Invite the bot to your designated channel using /invite @SDR Agent Notifier.

### **5\. Create the Prospect List**

Create a file named prospects.csv in the project root. It must contain headers that match the placeholders used in the email templates (e.g., FirstName, Company, Position).

FirstName,LastName,Email,Company,Position  
Jane,Doe,jane.doe@example.com,Example Corp,CTO

## **▶️ Running the Application**

This application requires **three separate terminal processes** to run locally.

### **Terminal 1: Start the Webhook Server**

This server listens for inbound email replies from SendGrid and interactive actions from Slack.

poetry run python webhook\_server.py

### **Terminal 2: Start the ngrok Tunnel**

This exposes your local webhook server to the internet.

\# Replace with your static domain if you have one  
ngrok http 8000 \--domain \<your.static.domain.ngrok-free.app\>

### **Terminal 3: Run the Outbound Campaign**

This script triggers the Sales\_Manager agent to start the email outreach campaign.

poetry run python -m app.main

## **🔮 Future Work & Roadmap**

This project has a solid foundation. The next steps to elevate it to a fully production-grade system include:

* **State Management & Memory:** Implement a database (e.g., SQLite or a cloud-based one) to store conversation history. This will allow the SDR\_Agent to have context for multi-turn conversations.  
* **Asynchronous Task Queue:** Decouple the long-running agent processes from the web server using a task queue like Celery with Redis. This will make the API more resilient and prevent webhook timeouts.  
* **Structured Logging:** Replace all print() statements with a structured JSON logger for better monitoring, debugging, and analysis in a production environment.  
* **Containerization:** Dockerize the entire application for consistent, environment-agnostic deployment.