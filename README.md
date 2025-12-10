# 🔒 Exam Integrity Monitor - MVP Demo

**Real-time AI Detection System for Saint Clair College**

## 🎯 What This Does

This Chrome/Edge extension monitors students during exams and **instantly flags** when they access AI tools like:
- ChatGPT
- Claude AI
- Google Gemini
- Microsoft Copilot
- And more...

**Key Features:**
- ✅ Real-time detection & screenshots
- ✅ Live dashboard for supervisors
- ✅ Works on Chrome AND Edge (same code!)
- ✅ Deploys via existing school admin controls
- ✅ Students can't disable it

---

## 🚀 Quick Start - Get Demo Running in 5 Minutes

### Step 1: Install Python Dependencies

```bash
cd exam-monitor
pip3 install flask flask-cors --break-system-packages
```

*Note: Use `--break-system-packages` on macOS or create a virtual environment*

### Step 2: Start the Dashboard Server

```bash
python3 server.py
```

You should see:
```
🚀 EXAM INTEGRITY MONITOR SERVER
📊 Dashboard: http://localhost:5000/dashboard
```

### Step 3: Install the Chrome Extension

1. Open **Chrome** (or Edge)
2. Go to `chrome://extensions/`
3. Enable **Developer mode** (toggle in top-right)
4. Click **"Load unpacked"**
5. Select the `exam-monitor` folder
6. Extension installed! ✅

### Step 4: Test It Live!

1. Open http://localhost:5000/dashboard in one browser window
2. Open https://chatgpt.com in another window
3. **BOOM!** 🚨 Instant flag appears on dashboard with screenshot!

---

## 📸 Demo Script for Presentation

### Setup Before Demo:
- Laptop with two browser windows side-by-side
- Left: Dashboard at `http://localhost:5000/dashboard`
- Right: Any normal website (Google, etc.)

### The Demo Flow:

**"Let me show you this running live..."**

1. Point to dashboard: *"This is the supervisor view. Currently clean."*

2. Switch to student browser: *"Here's a student taking an exam..."*

3. Type `chatgpt.com` and hit enter

4. **Immediately point to dashboard:**
   - *"Look! Instant alert!"*
   - *"Student ID, exact time, screenshot proof"*
   - *"Even if they close it in 2 seconds, we caught it"*

5. **The Killer Line:**
   *"Your IT department already controls these browsers - you saw how Saint Clair auto-opens tabs. This deploys the exact same way. We're just adding eyes to what students do during exams. No new infrastructure needed."*

---

## 🏗️ Project Structure

```
exam-monitor/
├── manifest.json      # Chrome extension config
├── background.js      # Monitoring logic (runs silently)
├── popup.html         # Extension UI (when clicked)
├── icon*.png          # Extension icons
├── server.py          # Flask backend + dashboard
└── README.md          # This file
```

---

## 🎨 Creating Extension Icons

The extension needs 3 icon sizes. You can:

**Option 1: Use Placeholder Icons (Quick)**
- Download any 3 PNG files (16x16, 48x48, 128x128)
- Rename them to `icon16.png`, `icon48.png`, `icon128.png`
- Put them in the `exam-monitor` folder

**Option 2: Use Online Icon Generator**
- Go to https://favicon.io/favicon-generator/
- Create a simple lock/shield icon
- Download and rename files

**Option 3: Create with Python (if Pillow installed)**
```bash
pip3 install Pillow --break-system-packages
python3 create_icons.py
```

---

## 💡 Technical Details

### How It Works:

1. **Extension monitors every tab change and URL access**
   - Runs silently in background
   - Students never see it

2. **Checks against blocked domain list**
   - ChatGPT, Claude, Gemini, etc.
   - Easy to add more

3. **Captures evidence & sends to server**
   - Screenshot taken instantly
   - Sent to dashboard in real-time
   - Stored locally if server unavailable

4. **Dashboard updates live**
   - Auto-refreshes every 3 seconds
   - Shows all flags with full evidence
   - Supervisor can monitor entire exam room

### Deployment in Real World:

**School IT pushes extension via:**
- Windows: Group Policy
- Mac: MDM (Jamf, etc.)
- ChromeOS: Admin Console

**Students can't:**
- Disable it (admin-enforced)
- Uninstall it (locked)
- Bypass it (monitors at browser level)

---

## 🔧 Customization

### Add More Blocked Sites:
Edit `background.js`, add to `BLOCKED_DOMAINS` array:
```javascript
const BLOCKED_DOMAINS = [
  'chatgpt.com',
  'claude.ai',
  'your-new-site.com',  // Add here
];
```

### Change Student ID:
In real deployment, this comes from school login system.
For demo, edit in `background.js`:
```javascript
let STUDENT_ID = 'DEMO-12345';  // Change this
```

### Customize Dashboard:
Edit the HTML template in `server.py` around line 30

---

## 📋 Next Steps for Production

**Phase 1 - Current MVP:**
- ✅ Local proof-of-concept
- ✅ Demo-ready

**Phase 2 - Pilot Program:**
- [ ] Database (SQLite/PostgreSQL)
- [ ] Student ID from school login
- [ ] Admin authentication
- [ ] Export reports (PDF/CSV)

**Phase 3 - Full Deployment:**
- [ ] Deploy server to cloud (AWS/Azure)
- [ ] Integrate with school LMS
- [ ] Advanced analytics
- [ ] Mobile admin app

---

## 🎓 Saint Clair College Integration

**Perfect fit because:**
1. ✅ You already control browsers (auto-tab proves it)
2. ✅ IT dept has deployment mechanisms ready
3. ✅ Works with existing exam lab computers
4. ✅ No student software installation needed
5. ✅ Instant ROI - catches cheating in real-time

---

## 🐛 Troubleshooting

**Extension not loading?**
- Make sure all files are in the folder
- Icon files must be present (use any PNG if needed)
- Check Chrome console for errors

**Dashboard not receiving flags?**
- Verify server is running (see terminal output)
- Check `http://localhost:5000/` loads
- Look for errors in Chrome extension console

**Screenshot not showing?**
- This is normal for some sites (browser security)
- URL and timestamp still captured

---

## 📞 Questions?

This is an MVP demo to prove the concept works.
Ready to show Saint Clair College how their existing infrastructure becomes an exam integrity powerhouse! 🚀

---

**Built for Saint Clair College**
*Making exam integrity simple, effective, and impossible to bypass.*
