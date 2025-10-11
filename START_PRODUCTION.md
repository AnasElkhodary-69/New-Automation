# Quick Start: Production Deployment

## 🚀 Getting Started (5 Minutes)

### Step 1: Choose Your Platform

#### Option A: Windows (Recommended for your setup)
```batch
cd D:\Projects\RAG-SDS\before-bert

REM Install NSSM (if not already installed)
REM Download from: https://nssm.cc/download

REM Run the installation script
deployment\install_windows_service.bat

REM Start the service
nssm start RAGEmailSystem

REM Check status
nssm status RAGEmailSystem
```

#### Option B: Linux (Production Server)
```bash
cd /path/to/before-bert

# Install supervisor
sudo apt-get install supervisor

# Edit the config file (update paths)
nano deployment/supervisor.conf

# Copy to supervisor directory
sudo cp deployment/supervisor.conf /etc/supervisor/conf.d/rag_email.conf

# Reload and start
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start rag_email_system

# Check status
sudo supervisorctl status rag_email_system
```

### Step 2: Start Health Monitoring (Optional but Recommended)

Open a new terminal:
```bash
python health_check.py
```

Then open in browser:
- Dashboard: http://localhost:8080/
- JSON API: http://localhost:8080/health

### Step 3: Verify It's Running

**Check health file:**
```bash
cat logs/health_status.txt
```

**Check logs:**
```bash
tail -f logs/daemon.log
```

**Check for emails being processed:**
```bash
# Wait 1-2 minutes, then check
tail -f logs/rag_email_system.log
```

---

## ⚙️ Configuration

### Email Check Interval
Edit `.env` file:
```bash
# Check emails every 60 seconds (default)
EMAIL_CHECK_INTERVAL=60

# For high volume (check every 30 seconds)
EMAIL_CHECK_INTERVAL=30

# For low volume (check every 5 minutes)
EMAIL_CHECK_INTERVAL=300
```

### Alert Email
Edit `.env` file:
```bash
# Email address to receive alerts
ADMIN_EMAIL=your-email@example.com
```

After changing .env, restart the service:
```bash
# Windows
nssm restart RAGEmailSystem

# Linux
sudo supervisorctl restart rag_email_system
```

---

## 🔍 Monitoring

### Real-time Monitoring
```bash
# Daemon log (system status)
tail -f logs/daemon.log

# Application log (email processing)
tail -f logs/rag_email_system.log

# Service log (Windows)
tail -f logs/service.log

# Health status
watch -n 5 cat logs/health_status.txt
```

### Check System Status
```bash
# Windows
nssm status RAGEmailSystem

# Linux (Supervisor)
sudo supervisorctl status rag_email_system

# Linux (Systemd)
sudo systemctl status rag_email_system
```

### View Logs
```bash
# Last 100 lines
tail -100 logs/daemon.log

# Follow in real-time
tail -f logs/daemon.log

# Search for errors
grep ERROR logs/daemon.log | tail -20

# Today's activity
grep "$(date +%Y-%m-%d)" logs/daemon.log
```

---

## 🛠️ Common Operations

### Restart Service
```bash
# Windows
nssm restart RAGEmailSystem

# Linux (Supervisor)
sudo supervisorctl restart rag_email_system

# Linux (Systemd)
sudo systemctl restart rag_email_system
```

### Stop Service
```bash
# Windows
nssm stop RAGEmailSystem

# Linux (Supervisor)
sudo supervisorctl stop rag_email_system

# Linux (Systemd)
sudo systemctl stop rag_email_system
```

### View Service Logs
```bash
# Windows
type logs\service.log
type logs\service_error.log

# Linux (Supervisor)
sudo supervisorctl tail rag_email_system
sudo supervisorctl tail rag_email_system stderr

# Linux (Systemd)
sudo journalctl -u rag_email_system -f
```

### Update Configuration
```bash
# 1. Edit .env file
nano .env

# 2. Restart service
nssm restart RAGEmailSystem  # Windows
sudo supervisorctl restart rag_email_system  # Linux
```

---

## 📧 Email Alerts

The system automatically sends email alerts for:
- ✅ System startup
- ❌ Critical errors (3+ consecutive failures)
- 🔄 System restart after crash
- 🛑 System shutdown

Configure alert email in `.env`:
```bash
ADMIN_EMAIL=your-email@example.com
```

---

## 🐛 Troubleshooting

### Service Won't Start
```bash
# Test manually first
cd D:\Projects\RAG-SDS\before-bert
python daemon_runner.py

# Check for errors in logs
cat logs/daemon.log | tail -50

# Verify Python path
where python  # Windows
which python3  # Linux
```

### No Emails Being Processed
```bash
# Test email connection
python -c "from email_module.email_reader import EmailReader; EmailReader().fetch_unread_emails()"

# Test Odoo connection
python tests/unit/test_odoo_connection.py

# Check if emails exist
# Log into your email account and verify unread emails
```

### High CPU/Memory Usage
```bash
# Restart the service
nssm restart RAGEmailSystem

# Check resource usage
# Windows: Task Manager
# Linux: htop or top
```

### Service Crashes Repeatedly
```bash
# Check error logs
cat logs/daemon.log | grep ERROR | tail -20
cat logs/service_error.log | tail -50

# Look for patterns (API rate limits, network issues, etc.)

# Increase check interval to reduce load
# Edit .env: EMAIL_CHECK_INTERVAL=300
```

---

## 📊 Performance Tuning

### For High Volume (100+ emails/day)
```bash
# .env settings
EMAIL_CHECK_INTERVAL=30  # Check every 30 seconds
```

### For Normal Volume (10-50 emails/day)
```bash
# .env settings (default)
EMAIL_CHECK_INTERVAL=60  # Check every 60 seconds
```

### For Low Volume (<10 emails/day)
```bash
# .env settings
EMAIL_CHECK_INTERVAL=300  # Check every 5 minutes
```

---

## 🔐 Security Checklist

- [ ] `.env` file has restricted permissions (chmod 600)
- [ ] Service runs as dedicated user (not root/admin)
- [ ] Firewall allows outbound SMTP/IMAP
- [ ] API keys are not in logs
- [ ] Log files have restricted access
- [ ] Backup .env file securely
- [ ] Regular security updates

---

## 📝 Daily Checklist

### Morning (2 minutes)
- [ ] Check service status: `nssm status RAGEmailSystem`
- [ ] Review health file: `cat logs/health_status.txt`
- [ ] Check for error alerts in email

### End of Day (3 minutes)
- [ ] Review email count processed
- [ ] Check error logs: `grep ERROR logs/daemon.log | tail -10`
- [ ] Verify disk space: `df -h`

### Weekly (10 minutes)
- [ ] Review performance metrics
- [ ] Check log file sizes
- [ ] Verify Odoo sync working
- [ ] Test manual email processing

---

## 🆘 Emergency Contacts

**If System is Down:**
1. Check service status
2. Review last 50 log lines
3. Try manual restart
4. If still failing, check network/API connections
5. Contact system administrator

**Log Locations:**
- Application: `logs/rag_email_system.log`
- Daemon: `logs/daemon.log`
- Service: `logs/service.log`
- Health: `logs/health_status.txt`

---

## 📚 Additional Resources

- Full deployment guide: `24_7_DEPLOYMENT_PLAN.md`
- Odoo sync guide: `SYNC_README.md`
- Troubleshooting: Check logs in `logs/` directory
- Health dashboard: http://localhost:8080/

---

**System Status: Production Ready ✅**
**Last Updated: 2025-10-11**
