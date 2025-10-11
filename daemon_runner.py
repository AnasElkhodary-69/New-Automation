"""
Production Daemon Runner for RAG Email System
Provides 24/7 reliability with auto-recovery, health monitoring, and alerting
"""

import os
import sys
import time
import logging
import traceback
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

# Import main system
from main import RAGEmailSystem

# ============================================================================
# CONFIGURATION
# ============================================================================

# Email check interval (seconds)
CHECK_INTERVAL = int(os.getenv('EMAIL_CHECK_INTERVAL', '60'))  # Default: 1 minute

# Error recovery settings
MAX_CONSECUTIVE_FAILURES = 3
RETRY_DELAY_SECONDS = 30
MAX_RETRY_DELAY = 300  # 5 minutes max

# Health check settings
HEALTH_CHECK_FILE = "logs/health_status.txt"
HEARTBEAT_INTERVAL = 300  # 5 minutes

# Alerting settings
ALERT_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@example.com')
ALERT_COOLDOWN_MINUTES = 60  # Don't spam alerts

# Logging
LOG_DIR = Path('logs')
LOG_DIR.mkdir(exist_ok=True)

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'daemon.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger('daemon')

# ============================================================================
# HEALTH MONITORING
# ============================================================================

class HealthMonitor:
    """Tracks system health and metrics"""

    def __init__(self):
        self.start_time = datetime.now()
        self.emails_processed = 0
        self.emails_failed = 0
        self.last_successful_process = None
        self.last_error = None
        self.consecutive_failures = 0
        self.last_alert_time = None

    def record_success(self, count: int = 1):
        """Record successful email processing"""
        self.emails_processed += count
        self.last_successful_process = datetime.now()
        self.consecutive_failures = 0
        self.update_health_file()

    def record_failure(self, error: str):
        """Record email processing failure"""
        self.emails_failed += 1
        self.consecutive_failures += 1
        self.last_error = error
        self.update_health_file()

    def reset_failures(self):
        """Reset failure counter"""
        self.consecutive_failures = 0

    def get_uptime(self) -> str:
        """Get formatted uptime"""
        delta = datetime.now() - self.start_time
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m {seconds}s"

    def update_health_file(self):
        """Write health status to file"""
        try:
            with open(HEALTH_CHECK_FILE, 'w') as f:
                f.write(f"Status: {'HEALTHY' if self.consecutive_failures < MAX_CONSECUTIVE_FAILURES else 'UNHEALTHY'}\n")
                f.write(f"Uptime: {self.get_uptime()}\n")
                f.write(f"Start Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Emails Processed: {self.emails_processed}\n")
                f.write(f"Emails Failed: {self.emails_failed}\n")
                f.write(f"Success Rate: {self.get_success_rate():.1f}%\n")
                f.write(f"Consecutive Failures: {self.consecutive_failures}\n")
                f.write(f"Last Successful Process: {self.last_successful_process or 'Never'}\n")
                f.write(f"Last Error: {self.last_error or 'None'}\n")
        except Exception as e:
            logger.error(f"Failed to update health file: {e}")

    def get_success_rate(self) -> float:
        """Calculate success rate percentage"""
        total = self.emails_processed + self.emails_failed
        if total == 0:
            return 100.0
        return (self.emails_processed / total) * 100

    def should_alert(self) -> bool:
        """Check if we should send an alert"""
        if self.consecutive_failures < MAX_CONSECUTIVE_FAILURES:
            return False

        if self.last_alert_time is None:
            return True

        time_since_alert = datetime.now() - self.last_alert_time
        return time_since_alert.total_seconds() > (ALERT_COOLDOWN_MINUTES * 60)

    def mark_alert_sent(self):
        """Record that an alert was sent"""
        self.last_alert_time = datetime.now()

# ============================================================================
# ALERTING SYSTEM
# ============================================================================

def send_alert_email(subject: str, message: str):
    """Send alert email to admin"""
    try:
        smtp_server = os.getenv('SMTP_SERVER')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        email_address = os.getenv('EMAIL_ADDRESS')
        email_password = os.getenv('EMAIL_PASSWORD')

        if not all([smtp_server, email_address, email_password]):
            logger.warning("Email credentials not configured, skipping alert")
            return

        msg = MIMEMultipart()
        msg['From'] = email_address
        msg['To'] = ALERT_EMAIL
        msg['Subject'] = f"[RAG Email System] {subject}"

        body = f"""
RAG Email System Alert
{'='*60}

{message}

Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{'='*60}
This is an automated message from RAG Email System.
"""
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(email_address, email_password)
            server.send_message(msg)

        logger.info(f"Alert email sent: {subject}")

    except Exception as e:
        logger.error(f"Failed to send alert email: {e}")

# ============================================================================
# DAEMON CORE
# ============================================================================

class DaemonRunner:
    """Main daemon runner with auto-recovery"""

    def __init__(self):
        self.health = HealthMonitor()
        self.system = None
        self.running = True
        self.retry_delay = RETRY_DELAY_SECONDS

    def initialize_system(self):
        """Initialize or reinitialize the RAG system"""
        try:
            logger.info("Initializing RAG Email System...")

            if self.system:
                # Clean up old system
                try:
                    self.system.shutdown()
                except Exception as e:
                    logger.warning(f"Error during shutdown: {e}")

            self.system = RAGEmailSystem()
            logger.info("System initialized successfully")
            self.health.reset_failures()
            self.retry_delay = RETRY_DELAY_SECONDS
            return True

        except Exception as e:
            error_msg = f"Failed to initialize system: {e}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.health.record_failure(error_msg)
            return False

    def process_emails_safe(self):
        """Process emails with error handling"""
        try:
            logger.info("Checking for new emails...")
            results = self.system.process_incoming_emails()

            if results:
                success_count = sum(1 for r in results if r.get('status') == 'processed')
                failed_count = len(results) - success_count

                logger.info(f"Processed {success_count} email(s) successfully, {failed_count} failed")

                if success_count > 0:
                    self.health.record_success(success_count)

                if failed_count > 0:
                    self.health.record_failure(f"{failed_count} emails failed processing")
            else:
                # No emails to process - this is normal
                logger.debug("No emails to process")

            return True

        except KeyboardInterrupt:
            raise
        except Exception as e:
            error_msg = f"Error processing emails: {e}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.health.record_failure(error_msg)

            # Check if we should alert
            if self.health.should_alert():
                send_alert_email(
                    "Critical: Multiple Consecutive Failures",
                    f"System has failed {self.health.consecutive_failures} times consecutively.\n\n"
                    f"Last Error: {error_msg}\n\n"
                    f"Uptime: {self.health.get_uptime()}\n"
                    f"Success Rate: {self.health.get_success_rate():.1f}%"
                )
                self.health.mark_alert_sent()

            return False

    def run(self):
        """Main daemon loop"""
        logger.info("="*80)
        logger.info("RAG Email System Daemon Starting...")
        logger.info(f"Check Interval: {CHECK_INTERVAL} seconds")
        logger.info(f"Health Check File: {HEALTH_CHECK_FILE}")
        logger.info(f"Alert Email: {ALERT_EMAIL}")
        logger.info("="*80)

        # Send startup notification
        send_alert_email(
            "System Started",
            f"RAG Email System has started successfully.\n\n"
            f"Check Interval: {CHECK_INTERVAL} seconds\n"
            f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        # Initial system setup
        if not self.initialize_system():
            logger.error("Failed to initialize system on startup")
            sys.exit(1)

        last_heartbeat = datetime.now()

        try:
            while self.running:
                # Process emails
                success = self.process_emails_safe()

                # Handle failures with exponential backoff
                if not success:
                    if self.health.consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                        logger.warning(f"Too many failures, attempting to reinitialize system...")
                        if not self.initialize_system():
                            logger.error(f"Reinitialization failed, waiting {self.retry_delay}s before retry...")
                            time.sleep(self.retry_delay)
                            # Exponential backoff
                            self.retry_delay = min(self.retry_delay * 2, MAX_RETRY_DELAY)
                            continue

                # Update heartbeat
                if (datetime.now() - last_heartbeat).total_seconds() >= HEARTBEAT_INTERVAL:
                    logger.info(f"Heartbeat - Uptime: {self.health.get_uptime()}, "
                               f"Processed: {self.health.emails_processed}, "
                               f"Failed: {self.health.emails_failed}, "
                               f"Success Rate: {self.health.get_success_rate():.1f}%")
                    last_heartbeat = datetime.now()

                # Wait for next check
                logger.info(f"Waiting {CHECK_INTERVAL} seconds before next check...")
                time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            logger.info("Received shutdown signal (Ctrl+C)")
        except Exception as e:
            logger.critical(f"Fatal error in daemon loop: {e}")
            logger.critical(traceback.format_exc())
            send_alert_email(
                "Critical: Daemon Crashed",
                f"The daemon has crashed with a fatal error:\n\n{e}\n\n"
                f"Uptime before crash: {self.health.get_uptime()}\n"
                f"Traceback:\n{traceback.format_exc()}"
            )
            raise
        finally:
            self.shutdown()

    def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down daemon...")
        self.running = False

        if self.system:
            try:
                self.system.shutdown()
            except Exception as e:
                logger.error(f"Error during system shutdown: {e}")

        # Send shutdown notification
        send_alert_email(
            "System Stopped",
            f"RAG Email System has stopped.\n\n"
            f"Total Uptime: {self.health.get_uptime()}\n"
            f"Emails Processed: {self.health.emails_processed}\n"
            f"Emails Failed: {self.emails_failed}\n"
            f"Success Rate: {self.health.get_success_rate():.1f}%\n"
            f"Stop Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        logger.info("Daemon stopped")

# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    """Main entry point"""
    try:
        daemon = DaemonRunner()
        daemon.run()
    except Exception as e:
        logger.critical(f"Failed to start daemon: {e}")
        logger.critical(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
