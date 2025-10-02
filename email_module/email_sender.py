"""
Email Sender Module

Handles sending emails via SMTP
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional, Dict
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class EmailSender:
    """Class to handle sending emails via SMTP"""

    def __init__(self, config_path: str = "config/email_config.json"):
        """
        Initialize Email Sender

        Args:
            config_path: Path to email configuration file
        """
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """
        Load email configuration from JSON file and environment variables

        Returns:
            Configuration dictionary with SMTP settings
        """
        logger.info(f"Loading email configuration from {self.config_path}")

        # Load from config_loader which prioritizes .env
        try:
            from config.config_loader import ConfigLoader
            loader = ConfigLoader()
            return loader.load_email_config()
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "email": "",
                "password": "",
                "use_tls": True
            }

    def send_email(
        self,
        to_address: str,
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[str]] = None,
        body_html: Optional[str] = None
    ) -> bool:
        """
        Send an email

        Args:
            to_address: Recipient email address
            subject: Email subject
            body: Plain text email body
            cc: List of CC recipients
            bcc: List of BCC recipients
            attachments: List of file paths to attach
            body_html: HTML version of email body

        Returns:
            True if sent successfully, False otherwise
        """
        logger.info(f"Sending email to {to_address}")

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.config['email']
            msg['To'] = to_address
            msg['Subject'] = subject

            if cc:
                msg['Cc'] = ', '.join(cc)

            # Attach text body
            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)

            # Attach HTML body if provided
            if body_html:
                html_part = MIMEText(body_html, 'html')
                msg.attach(html_part)

            # Attach files if provided
            if attachments:
                for file_path in attachments:
                    self._attach_file(msg, file_path)

            # Send email
            self._send_message(msg, to_address, cc, bcc)

            logger.info("Email sent successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False

    def send_reply(
        self,
        to_address: str,
        subject: str,
        body: str,
        in_reply_to: Optional[str] = None,
        references: Optional[str] = None,
        body_html: Optional[str] = None
    ) -> bool:
        """
        Send a reply email

        Args:
            to_address: Recipient email address
            subject: Email subject (usually with Re: prefix)
            body: Email body
            in_reply_to: Message-ID of email being replied to
            references: References header for threading
            body_html: HTML version of body

        Returns:
            True if sent successfully, False otherwise
        """
        logger.info(f"Sending reply to {to_address}")

        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.config['email']
            msg['To'] = to_address
            msg['Subject'] = subject

            # Add threading headers for proper reply chain
            if in_reply_to:
                msg['In-Reply-To'] = in_reply_to
            if references:
                msg['References'] = references

            # Attach body
            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)

            if body_html:
                html_part = MIMEText(body_html, 'html')
                msg.attach(html_part)

            self._send_message(msg, to_address)

            logger.info("Reply sent successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to send reply: {str(e)}")
            return False

    def _attach_file(self, msg: MIMEMultipart, file_path: str):
        """
        Attach a file to email message

        Args:
            msg: Email message object
            file_path: Path to file to attach
        """
        try:
            path = Path(file_path)
            if not path.exists():
                logger.error(f"Attachment file not found: {file_path}")
                return

            # Read file
            with open(path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())

            # Encode file
            encoders.encode_base64(part)

            # Add header
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {path.name}'
            )

            msg.attach(part)
            logger.info(f"Attached file: {path.name}")

        except Exception as e:
            logger.error(f"Error attaching file {file_path}: {e}")

    def _send_message(
        self,
        msg: MIMEMultipart,
        to_address: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ):
        """
        Send the email message via SMTP

        Args:
            msg: Prepared email message
            to_address: Primary recipient
            cc: CC recipients
            bcc: BCC recipients
        """
        try:
            # Build recipient list
            recipients = [to_address]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)

            # Connect and send
            if self.config.get('use_tls'):
                server = smtplib.SMTP(
                    self.config['smtp_server'],
                    self.config['smtp_port']
                )
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(
                    self.config['smtp_server'],
                    self.config['smtp_port']
                )

            server.login(self.config['email'], self.config['password'])
            server.sendmail(self.config['email'], recipients, msg.as_string())
            server.quit()

            logger.info(f"Message sent to {len(recipients)} recipient(s)")

        except Exception as e:
            logger.error(f"Error sending message via SMTP: {str(e)}")
            raise

    def send_bulk_emails(self, email_list: List[Dict]) -> Dict[str, int]:
        """
        Send multiple emails

        Args:
            email_list: List of email dictionaries with to, subject, body

        Returns:
            Dictionary with success and failure counts
        """
        logger.info(f"Sending {len(email_list)} emails")

        results = {
            'success': 0,
            'failed': 0
        }

        for email_data in email_list:
            success = self.send_email(
                to_address=email_data['to'],
                subject=email_data['subject'],
                body=email_data['body']
            )
            if success:
                results['success'] += 1
            else:
                results['failed'] += 1

        logger.info(f"Bulk send complete: {results['success']} sent, {results['failed']} failed")
        return results

    def validate_email_address(self, email: str) -> bool:
        """
        Validate email address format

        Args:
            email: Email address to validate

        Returns:
            True if valid, False otherwise
        """
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
