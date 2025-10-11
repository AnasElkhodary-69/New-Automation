# 24/7 Production Deployment Plan
## RAG Email System - Zero Downtime Strategy

---

## 📋 Table of Contents
1. [Current Architecture Analysis](#current-architecture-analysis)
2. [Reliability Strategy](#reliability-strategy)
3. [Implementation Steps](#implementation-steps)
4. [Monitoring & Alerts](#monitoring--alerts)
5. [Deployment Guide](#deployment-guide)
6. [Maintenance & Troubleshooting](#maintenance--troubleshooting)

---

## 🏗️ Current Architecture Analysis

### Main Components
```
main.py (RAGEmailSystem class)
├── Email Reader (IMAP connection)
├── Email Sender (SMTP connection)
├── Odoo Connector (XML-RPC)
├── Vector Store (JSON-based)
├── Mistral AI Agent (API calls)
└── Email Processor (orchestration)
```

### Current Features
✅ `run_continuous()` method exists (line 520)
✅ Graceful shutdown handling
✅ File-based logging
✅ Error handling in workflow
✅ Configuration via .env

### Potential Failure Points
❌ **Network Issues**: IMAP/SMTP/Odoo/API disconnections
❌ **API Rate Limits**: Mistral AI throttling
❌ **Memory Leaks**: Long-running Python processes
❌ **Email Malformations**: Parsing errors
❌ **Odoo Downtime**: Database unavailable
❌ **Disk Space**: Logs filling up
❌ **Process Crashes**: Unhandled exceptions

---

## 🛡️ Reliability Strategy

### Layer 1: Process Management
**Tool**: Supervisor (Linux) or NSSM (Windows Service)
- Auto-restart on crash
- Configurable retry delays
- Resource limits

### Layer 2: Error Recovery
**Implementation**: Enhanced try-catch with exponential backoff
- Retry failed emails
- Skip problematic emails
- Queue management

### Layer 3: Health Monitoring
**Tools**: Watchdog + Health Check Endpoint
- Heartbeat monitoring
- Email processing metrics
- Resource usage tracking

### Layer 4: Alerting
**Methods**: Email + Log monitoring
- Critical error notifications
- Daily summary reports
- Performance degradation alerts

### Layer 5: Data Persistence
**Strategy**: Queue-based processing
- Failed emails queue
- Processing state persistence
- Graceful recovery after restart

---

## 🚀 Implementation Steps

### Step 1: Enhanced Main Runner with Auto-Recovery
```python
# daemon_runner.py - Production-grade daemon
```

### Step 2: Health Check System
```python
# health_check.py - HTTP endpoint for monitoring
```

### Step 3: Process Management
**Linux (Supervisor)**
```ini
[program:rag_email_system]
command=/path/to/python daemon_runner.py
autostart=true
autorestart=true
startretries=999999
```

**Windows (NSSM)**
```batch
nssm install RAGEmailSystem "C:\Python\python.exe" "D:\Projects\RAG-SDS\before-bert\daemon_runner.py"
nssm set RAGEmailSystem AppDirectory "D:\Projects\RAG-SDS\before-bert"
nssm start RAGEmailSystem
```

### Step 4: Monitoring Dashboard
- Simple web interface showing status
- Recent emails processed
- Error count
- Uptime

### Step 5: Alerting System
- Email alerts for critical errors
- Daily summary emails
- Log rotation

---

## 📊 Monitoring & Alerts

### Health Metrics to Track
1. **System Health**
   - Uptime
   - Memory usage
   - CPU usage
   - Disk space

2. **Email Metrics**
   - Emails processed (hourly/daily)
   - Success rate
   - Average processing time
   - Queue length

3. **Component Health**
   - IMAP connection status
   - Odoo connection status
   - Mistral API status
   - Last successful email

4. **Error Tracking**
   - Error count (by type)
   - Failed emails list
   - Retry attempts

### Alert Triggers
🚨 **Critical** (Immediate notification)
- System crash/restart
- 3+ consecutive failures
- Odoo connection lost
- API authentication failure

⚠️ **Warning** (Daily summary)
- Single email failure
- Slow processing (>2 min)
- High memory usage
- Log file size >100MB

ℹ️ **Info** (Daily report)
- Emails processed count
- Success rate
- System uptime
- Performance stats

---

## 📦 Deployment Architecture

### Recommended Setup

```
Production Server
│
├── Application Layer
│   ├── main.py (core system)
│   ├── daemon_runner.py (wrapper with recovery)
│   ├── health_check.py (HTTP endpoint)
│   └── incremental_sync_odoo.py (scheduled sync)
│
├── Process Management
│   ├── Supervisor (Linux) or NSSM (Windows)
│   └── Auto-restart on failure
│
├── Monitoring
│   ├── Health check HTTP endpoint (:8080/health)
│   ├── Log monitoring (tail -f logs/)
│   └── Optional: Uptime Kuma / Prometheus
│
├── Scheduled Tasks
│   ├── Odoo Sync (every 5-15 min)
│   ├── Log rotation (daily)
│   └── Backup (daily)
│
└── Alerting
    ├── Email notifications (critical errors)
    ├── Daily summary emails
    └── Log file monitoring
```

---

## 🔧 Implementation Priority

### Phase 1: Essential (Must Have) ✅
1. ✅ Daemon runner with auto-recovery
2. ✅ Enhanced error handling
3. ✅ Process supervisor (NSSM/Supervisor)
4. ✅ Basic health checks
5. ✅ Email alerting for critical errors

### Phase 2: Important (Should Have) 📋
6. 📋 Health check HTTP endpoint
7. 📋 Failed email queue
8. 📋 Daily summary reports
9. 📋 Log rotation automation
10. 📋 Resource monitoring

### Phase 3: Nice to Have (Could Have) 💡
11. 💡 Web dashboard
12. 💡 Grafana/Prometheus integration
13. 💡 Advanced metrics
14. 💡 Performance profiling
15. 💡 A/B testing framework

---

## 🎯 Quick Start Guide

### Option A: Linux Production (Recommended)
```bash
# 1. Install supervisor
sudo apt-get install supervisor

# 2. Copy supervisor config
sudo cp deployment/supervisor.conf /etc/supervisor/conf.d/rag_email.conf

# 3. Start service
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start rag_email_system

# 4. Check status
sudo supervisorctl status rag_email_system
```

### Option B: Windows Production
```batch
REM 1. Install NSSM
REM Download from https://nssm.cc/download

REM 2. Install service
nssm install RAGEmailSystem "C:\Python\python.exe" ^
  "D:\Projects\RAG-SDS\before-bert\daemon_runner.py"

REM 3. Configure service
nssm set RAGEmailSystem AppDirectory "D:\Projects\RAG-SDS\before-bert"
nssm set RAGEmailSystem AppStdout "D:\Projects\RAG-SDS\before-bert\logs\service.log"
nssm set RAGEmailSystem AppStderr "D:\Projects\RAG-SDS\before-bert\logs\service_error.log"

REM 4. Start service
nssm start RAGEmailSystem

REM 5. Check status
nssm status RAGEmailSystem
```

### Option C: Docker (Advanced)
```bash
# 1. Build image
docker build -t rag-email-system .

# 2. Run container with restart policy
docker run -d \
  --name rag-email-system \
  --restart unless-stopped \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/odoo_database:/app/odoo_database \
  --env-file .env \
  rag-email-system

# 3. Check logs
docker logs -f rag-email-system
```

---

## 🔍 Monitoring Commands

### Check System Status
```bash
# Linux (Supervisor)
sudo supervisorctl status rag_email_system
sudo supervisorctl tail rag_email_system

# Windows (NSSM)
nssm status RAGEmailSystem
type logs\service.log
```

### View Logs
```bash
# Main application log
tail -f logs/rag_email_system.log

# Error log only
tail -f logs/rag_email_system.log | grep ERROR

# Health check log
tail -f logs/health_check.log
```

### Check Health Endpoint
```bash
# If health check server is running
curl http://localhost:8080/health

# Expected response:
# {
#   "status": "healthy",
#   "uptime": "2d 5h 32m",
#   "emails_processed": 1250,
#   "last_email": "2025-10-11 14:32:15",
#   "error_count": 3
# }
```

---

## 🚨 Troubleshooting

### Problem: Service won't start
**Check:**
```bash
# Verify Python path
which python3

# Test manually
cd /path/to/before-bert
python3 daemon_runner.py

# Check logs
cat logs/rag_email_system.log | tail -100
```

### Problem: Email processing stopped
**Check:**
```bash
# Verify IMAP connection
python3 -c "from email_module.email_reader import EmailReader; EmailReader()"

# Verify Odoo connection
python3 tests/unit/test_odoo_connection.py

# Check for stuck processes
ps aux | grep python
```

### Problem: High memory usage
**Solution:**
```bash
# Restart service
sudo supervisorctl restart rag_email_system

# Check memory before/after
free -h
```

### Problem: Logs filling disk
**Solution:**
```bash
# Set up log rotation
sudo nano /etc/logrotate.d/rag_email

# Add configuration:
/path/to/logs/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
}
```

---

## 📈 Performance Tuning

### Email Check Interval
```python
# In daemon_runner.py
CHECK_INTERVAL = 60  # seconds

# Recommendations:
# - High volume: 30 seconds
# - Normal: 60 seconds
# - Low volume: 300 seconds (5 min)
```

### Connection Pooling
```python
# Reuse connections instead of reconnecting
# Already implemented in OdooConnector
```

### Batch Processing
```python
# Process multiple emails in one cycle
# Already implemented in process_incoming_emails()
```

---

## 🔒 Security Considerations

1. **Credentials Management**
   - Use `.env` for sensitive data
   - Never commit `.env` to git
   - Restrict file permissions: `chmod 600 .env`

2. **Service User**
   - Run as dedicated user (not root)
   - Limited permissions
   - `sudo useradd -m -s /bin/bash rag_email`

3. **Network Security**
   - Firewall rules for outbound SMTP/IMAP
   - API key rotation policy
   - HTTPS for webhooks

4. **Log Security**
   - Don't log passwords/API keys
   - Rotate logs regularly
   - Restrict log file access

---

## 📝 Daily Operations Checklist

### Morning Check (5 min)
- [ ] Check service status
- [ ] Review overnight logs for errors
- [ ] Verify email processing count
- [ ] Check disk space

### Weekly Maintenance (15 min)
- [ ] Review error patterns
- [ ] Check API usage/costs
- [ ] Verify Odoo sync working
- [ ] Update JSON databases if needed
- [ ] Review performance metrics

### Monthly Tasks (30 min)
- [ ] Review and clean logs
- [ ] Update dependencies
- [ ] Performance optimization
- [ ] Backup configuration
- [ ] Security audit

---

## 📞 Support & Escalation

### Level 1: Automatic Recovery
- Process crashes → Auto-restart
- Network timeouts → Retry logic
- Single email failures → Skip and continue

### Level 2: Monitoring Alerts
- Email notification to admin
- Log aggregation for analysis
- Automatic ticket creation

### Level 3: Manual Intervention
- Service restart required
- Configuration changes needed
- Database maintenance

---

## 🎓 Best Practices

1. **Always test in staging first**
2. **Keep .env backed up securely**
3. **Monitor logs for first 48 hours after deployment**
4. **Set up alerting before going live**
5. **Document any custom changes**
6. **Schedule maintenance windows**
7. **Keep Python dependencies updated**
8. **Test recovery procedures regularly**

---

**Next Steps**: Implement Phase 1 components (daemon runner, error handling, process supervisor)
