# Facebook DealMachine Followers Scraper (Python + Selenium + Jenkins)

This project automates the extraction of follower profile data from the **DealMachine Facebook page** and saves the results into an Excel file.

It is **Jenkins-ready**, supports **automatic Facebook login using credentials**, and can resume scraping without duplicating records.

---

## ✨ Features

- ✅ Automatic Facebook login (username & password via environment variables)
- ✅ Works in **Jenkins (headless-safe, no popups)**
- ✅ Extracts follower profile data:
  - Facebook Name
  - Profile URL
  - Email
  - Phone
  - Website
  - External Facebook / LinkedIn / Instagram
- ✅ Saves data to Excel (`.xlsx`)
- ✅ Resume capability (avoids duplicate records)
- ✅ ChromeDriver auto-managed using `webdriver-manager`

---

## 🛠 Tech Stack

- **Python 3**
- **Selenium WebDriver**
- **Chrome / ChromeDriver**
- **openpyxl** (Excel handling)
- **BeautifulSoup** (optional, for parsing)
- **Jenkins** (CI execution)

---

## 📂 Project Structure

facebook-dealmachine-scraper/
│
├── facebook_dealmachine_scraper.py
├── facebook_dealmachine_results.xlsx
├── README.md


---

## 🔐 Facebook Login (Required)

⚠ **Do NOT hard-code credentials**

This script reads Facebook credentials from environment variables:

```text
FB_USERNAME
FB_PASSWORD
▶️ Run Locally
1️⃣ Install dependencies
pip install selenium webdriver-manager openpyxl beautifulsoup4
2️⃣ Set environment variables
Windows (PowerShell)
setx FB_USERNAME "your_facebook_email"
setx FB_PASSWORD "your_facebook_password"
Linux / macOS
export FB_USERNAME="your_facebook_email"
export FB_PASSWORD="your_facebook_password"
3️⃣ Run the script
python facebook_dealmachine_scraper.py
🤖 Run in Jenkins
1️⃣ Add Jenkins Credentials
Kind: Username with password

ID: FB_LOGIN

Username: Facebook email

Password: Facebook password

2️⃣ Jenkinsfile (Windows Agent)
pipeline {
    agent any

    environment {
        FB_USERNAME = credentials('FB_LOGIN').username
        FB_PASSWORD = credentials('FB_LOGIN').password
    }

    stages {
        stage('Run Facebook Scraper') {
            steps {
                bat 'python facebook_dealmachine_scraper.py'
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: '*.xlsx', fingerprint: true
        }
    }
}
📊 Output
Data is saved to:

facebook_dealmachine_results.xlsx
Existing rows are updated if missing data

New profiles are appended

Duplicate scraping is avoided

⚠️ Important Notes
Facebook actively detects automation

You may face:

Login checkpoints

OTP / verification

Temporary account restrictions

Run at low speed and avoid frequent executions

🚀 Recommended Enhancements
✅ Chrome user profile login (most stable)

✅ Headless mode for Linux Jenkins agents

✅ Proxy / rate-limiting support

✅ Dockerized execution

✅ Logging instead of print

📌 Disclaimer
This project is for educational and testing purposes only.
Automating Facebook may violate their Terms of Service.
Use responsibly and at your own risk.

