import imaplib
import email
from email.header import decode_header
import os
from langchain.tools import tool
from langchain_community.utilities import SerpAPIWrapper
from backend.config import SERPAPI_KEY, EMAIL_ADDRESS, EMAIL_PASSWORD, IMAP_SERVER, SMTP_SERVER, SMTP_PORT

@tool()
def read_emails(query: str) -> str:
    """
    Use this tool to fetch and read emails from the user's inbox.
    
    Guidelines for the AI:
    - Use this when the user wants to check their emails, see messages, or find specific emails.
    - The query should describe what emails to fetch (e.g., "recent 5 emails", "emails from boss", "unread emails about meeting")
    - Parse the user's natural language query to extract: sender, subject keywords, count, and unread filter
    - Always provide a friendly summary of the emails found
    
    Example usage:
    - "Show me my recent emails"
    - "Check emails from john@example.com"
    - "Find unread emails about invoice"
    - "Get 10 latest emails"
    
    Returns:
    - A formatted string with email details (sender, subject, date, body preview)
    """
    print("email reader tool used")
    
    try:
        # Get email credentials from environment
        email_address = os.getenv("EMAIL_ADDRESS")
        email_password = os.getenv("EMAIL_PASSWORD")
        imap_server = os.getenv("IMAP_SERVER", "imap.gmail.com")
        
        if not email_address or not email_password:
            return (
                "❌ Email credentials not set. Please set EMAIL_ADDRESS and EMAIL_PASSWORD "
                "environment variables. For Gmail, use an App Password from: "
                "https://myaccount.google.com/apppasswords"
            )
        
        # Parse query to extract parameters
        query_lower = query.lower()
        
        # Extract count
        count = 5  # default
        for word in query.split():
            if word.isdigit():
                count = min(int(word), 20)  # Cap at 20 for performance
                break
        
        # Check for unread filter
        unread_only = "unread" in query_lower
        
        # Extract sender (look for email pattern or "from X")
        sender = None
        if "from " in query_lower:
            parts = query_lower.split("from ")
            if len(parts) > 1:
                sender_part = parts[1].split()[0].strip()
                if "@" in sender_part or sender_part:
                    sender = sender_part
        
        # Extract subject keywords
        subject = None
        if "about " in query_lower:
            parts = query_lower.split("about ")
            if len(parts) > 1:
                subject = parts[1].split()[0].strip()
        elif "subject " in query_lower:
            parts = query_lower.split("subject ")
            if len(parts) > 1:
                subject = parts[1].split()[0].strip()
        
        # Connect to email server
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(email_address, email_password)
        mail.select("inbox")
        
        # Build search criteria
        criteria = []
        if unread_only:
            criteria.append("UNSEEN")
        if sender:
            criteria.append(f'FROM "{sender}"')
        if subject:
            criteria.append(f'SUBJECT "{subject}"')
        
        search_criteria = " ".join(criteria) if criteria else "ALL"
        
        # Search for emails
        status, messages = mail.search(None, search_criteria)
        
        if status != "OK":
            return "❌ Error searching emails."
        
        email_ids = messages[0].split()
        
        if not email_ids:
            return f"📭 No emails found matching: {query}"
        
        # Get most recent emails
        email_ids = email_ids[-count:]
        email_ids.reverse()
        
        results = []
        
        for email_id in email_ids:
            status, msg_data = mail.fetch(email_id, "(RFC822)")
            
            if status != "OK":
                continue
            
            # Parse email
            msg = email.message_from_bytes(msg_data[0][1])
            
            # Decode header
            def decode_str(s):
                if s is None:
                    return ""
                decoded = decode_header(s)
                result = []
                for content, encoding in decoded:
                    if isinstance(content, bytes):
                        try:
                            result.append(content.decode(encoding or 'utf-8', errors='ignore'))
                        except:
                            result.append(content.decode('utf-8', errors='ignore'))
                    else:
                        result.append(str(content))
                return ''.join(result)
            
            # Extract body
            def get_body(msg):
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            try:
                                body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                                break
                            except:
                                pass
                else:
                    try:
                        body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                    except:
                        body = str(msg.get_payload())
                return body.strip()
            
            subject_text = decode_str(msg.get("Subject", ""))
            from_text = decode_str(msg.get("From", ""))
            date_text = msg.get("Date", "")
            body_text = get_body(msg)
            
            # Truncate body
            if len(body_text) > 300:
                body_text = body_text[:300] + "..."
            
            results.append({
                "from": from_text,
                "subject": subject_text,
                "date": date_text,
                "body": body_text
            })
        
        mail.close()
        mail.logout()
        
        # Format output
        if not results:
            return "📭 No emails found."
        
        output = f"📧 Found {len(results)} email(s):\n\n"
        for i, em in enumerate(results, 1):
            output += f"--- Email {i} ---\n"
            output += f"From: {em['from']}\n"
            output += f"Subject: {em['subject']}\n"
            output += f"Date: {em['date']}\n"
            output += f"Preview: {em['body'][:200]}...\n\n"
        
        return output
        
    except imaplib.IMAP4.error as e:
        return f"❌ Email login failed: {str(e)}. Check your credentials and App Password."
    except Exception as e:
        return f"❌ Error reading emails: {str(e)}"


@tool()
def send_email(query: str) -> str:
    """
    Use this tool to send emails to recipients.
    
    Guidelines for the AI:
    - Use this when the user wants to send an email, compose a message, or email someone.
    - The query should contain: recipient email, subject, and message body
    - Parse natural language to extract these components
    - Always confirm what will be sent before actually sending
    - Be helpful in composing professional or casual emails based on user's tone
    
    Expected query format (flexible):
    - "Send email to john@example.com with subject 'Meeting' and message 'Hi, let's meet tomorrow'"
    - "Email boss@company.com about the project update: We completed phase 1"
    - "Compose email to friend@gmail.com saying hello and asking about weekend plans"
    
    Returns:
    - Success message with details of sent email, or error message if something fails
    """
    print("send email tool used")
    
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # Get email credentials
        email_address = EMAIL_ADDRESS
        email_password = EMAIL_PASSWORD
        smtp_server = SMTP_SERVER
        smtp_port = SMTP_PORT

        if not email_address or not email_password:
            return (
                "❌ Email credentials not set. Please set EMAIL_ADDRESS and EMAIL_PASSWORD "
                "environment variables."
            )
        
        # Parse query to extract recipient, subject, and body
        query_lower = query.lower()
        
        # Extract recipient email (look for email pattern)
        import re
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails_found = re.findall(email_pattern, query)
        
        if not emails_found:
            return "❌ No recipient email address found. Please provide a valid email address (e.g., user@example.com)"
        
        recipient = emails_found[0]
        
        # Extract subject
        subject = "No Subject"
        if "subject" in query_lower:
            # Look for text after "subject" keyword
            parts = query.split("subject", 1)
            if len(parts) > 1:
                subject_part = parts[1].strip()
                # Extract until "message" or "body" or email body indicators
                for delimiter in [" message ", " body ", " saying ", " and message ", ":"]:
                    if delimiter in subject_part.lower():
                        subject = subject_part.split(delimiter)[0].strip(' "\'"')
                        break
                else:
                    # Take first sentence or phrase
                    subject = subject_part.split('.')[0].strip(' "\'"')[:100]
        elif "about" in query_lower:
            # "email X about Y"
            parts = query.lower().split("about", 1)
            if len(parts) > 1:
                subject_part = parts[1].strip()
                # Extract until message body indicators
                for delimiter in [":", " saying ", " message ", " body "]:
                    if delimiter in subject_part:
                        subject = subject_part.split(delimiter)[0].strip(' "\'"')
                        break
                else:
                    subject = subject_part.split('.')[0].strip(' "\'"')[:100]
        
        # Extract message body
        body = ""
        body_indicators = ["message:", "body:", "saying:", "message ", "body ", "saying "]
        
        for indicator in body_indicators:
            if indicator in query_lower:
                parts = query.split(indicator, 1)
                if len(parts) > 1:
                    body = parts[1].strip(' "\'"')
                    break
        
        # If no explicit body found, try to extract after subject
        if not body:
            # Look for content after subject line
            if "subject" in query_lower and ":" in query:
                parts = query.split(":", 1)
                if len(parts) > 1:
                    potential_body = parts[1].strip()
                    # Remove email address if it appears
                    for email_addr in emails_found:
                        potential_body = potential_body.replace(email_addr, "").strip()
                    if potential_body and len(potential_body) > 10:
                        body = potential_body
        
        if not body:
            return f"❌ No email message body found. Please provide the message content you want to send to {recipient}"
        
        # Create email
        msg = MIMEMultipart()
        msg['From'] = email_address
        msg['To'] = recipient
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(email_address, email_password)
            server.send_message(msg)
        
        return f"""✅ Email sent successfully!

            To: {recipient}
            Subject: {subject}
            Message: {body[:200]}{'...' if len(body) > 200 else ''}

            Your email has been delivered! 📧
        """
                
    except smtplib.SMTPAuthenticationError:
        return "❌ Email authentication failed. Check your EMAIL_PASSWORD (use App Password for Gmail)."
    except smtplib.SMTPException as e:
        return f"❌ Failed to send email: {str(e)}"
    except Exception as e:
        return f"❌ Error sending email: {str(e)}"



# Pass the key explicitly
# search = SerpAPIWrapper(serpapi_api_key=SERPAPI_KEY)

if __name__ == "__main__":
    print("how far are jaipur and jodhpur")
    # Uncomment to test email tools:
    # print(read_emails.run("show me 3 recent emails"))
    # print(send_email.run("send email to test@example.com subject 'Test' message 'Hello World'"))