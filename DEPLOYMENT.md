# Cricket Analytics Dashboard — AWS Deployment Guide

Step-by-step instructions to deploy on **AWS Free Tier EC2** (t2.micro / t3.micro).

---

## 1. Launch EC2 Instance

- **AMI:** Ubuntu 22.04 LTS (Free Tier eligible)
- **Instance type:** t2.micro (1 vCPU, 1 GB RAM)
- **Storage:** 8 GB gp3 (Free Tier allows up to 30 GB)
- **Security Group:** Allow inbound TCP ports **22** (SSH) and **8501** (Streamlit)

## 2. Connect & Install System Dependencies

```bash
ssh -i your-key.pem ubuntu@<your-ec2-ip>

sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv git -y
```

## 3. Clone the Project

```bash
git clone <your-repo-url> ~/cricket_dashboard
cd ~/cricket_dashboard
```

Or upload via `scp`:

```bash
scp -i your-key.pem -r cricket_dashboard/ ubuntu@<your-ec2-ip>:~/
```

## 4. Create Virtual Environment & Install Dependencies

```bash
cd ~/cricket_dashboard
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 5. Initialise the Database

```bash
python3 -c "from database.db_manager import CricketDB; db = CricketDB(); db.init_db(); print('Database initialised')"
```

## 6. Run Scrapers (Initial Data Load)

```bash
cd scraper

# Run each spider (they write directly to SQLite)
scrapy crawl teams
scrapy crawl players
scrapy crawl series
scrapy crawl matches

cd ..
```

> **Note:** Each spider respects a 2-3 second delay between requests. Full crawl takes ~10-15 minutes.

## 7. Start Streamlit Dashboard

```bash
streamlit run app.py \
  --server.port 8501 \
  --server.headless true \
  --server.maxUploadSize 1 \
  --server.enableCORS false
```

Access at: `http://<your-ec2-ip>:8501`

## 8. Run as a Background Service (systemd)

Create a systemd service so the dashboard starts on boot:

```bash
sudo tee /etc/systemd/system/cricket-dashboard.service > /dev/null <<EOF
[Unit]
Description=Cricket Analytics Dashboard
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/cricket_dashboard
ExecStart=/home/ubuntu/cricket_dashboard/venv/bin/streamlit run app.py --server.port 8501 --server.headless true
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable cricket-dashboard
sudo systemctl start cricket-dashboard
```

Check status:

```bash
sudo systemctl status cricket-dashboard
```

## 9. Scheduled Data Refresh (cron)

Add a cron job to refresh data daily at 2 AM:

```bash
crontab -e
```

Add:

```cron
0 2 * * * cd /home/ubuntu/cricket_dashboard/scraper && /home/ubuntu/cricket_dashboard/venv/bin/scrapy crawl teams && /home/ubuntu/cricket_dashboard/venv/bin/scrapy crawl players && /home/ubuntu/cricket_dashboard/venv/bin/scrapy crawl series && /home/ubuntu/cricket_dashboard/venv/bin/scrapy crawl matches >> /home/ubuntu/cricket_dashboard/cron.log 2>&1
```

## 10. Memory Optimisation for 1 GB RAM

The app is designed to stay under 500 MB:

- **SQLite** file stays under 5 MB for typical dataset
- **Scrapy** runs one spider at a time with `CONCURRENT_REQUESTS=4`
- **Streamlit** uses `@st.cache_data(ttl=300)` — 5 min cache
- **Queries** use `LIMIT` clauses (default 200 rows)

If memory is tight, add a swap file:

```bash
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

## Security Checklist

- ✅ All SQL queries use parameterized statements (no string formatting)
- ✅ Streamlit input validated before database queries
- ✅ No secrets or credentials in code
- ✅ Security group limits inbound to ports 22 and 8501
- ✅ Consider adding an Nginx reverse proxy for HTTPS in production
