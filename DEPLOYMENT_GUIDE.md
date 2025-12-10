# 🚀 Deploy to Production for Tomorrow's Demo

## Quick Deploy to Render.com (10 Minutes)

### Step 1: Create GitHub Repository (2 minutes)

```bash
cd /Users/admin/Downloads/exama/exam-monitor

# Initialize git (if not already)
git init

# Create .gitignore
echo "__pycache__/" > .gitignore
echo "*.pyc" >> .gitignore
echo ".DS_Store" >> .gitignore

# Add all files
git add .

# Commit
git commit -m "Initial commit: Exam Integrity Monitor MVP"

# Create GitHub repo (go to github.com/new)
# Then push:
git remote add origin https://github.com/YOUR-USERNAME/exam-monitor.git
git branch -M main
git push -u origin main
```

---

### Step 2: Deploy to Render (5 minutes)

1. **Go to:** https://render.com
2. **Sign up** with GitHub (free, no credit card)
3. **Click "New +" → "Web Service"**
4. **Connect your `exam-monitor` repository**
5. **Settings:**
   ```
   Name: exam-monitor
   Environment: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: gunicorn server:app
   Plan: Free
   ```
6. **Click "Create Web Service"**
7. **Wait 2-3 minutes** for deployment
8. **Get your URL:** `https://exam-monitor.onrender.com`

---

### Step 3: Update Extension for Production (3 minutes)

**Edit `background.js`:**

Change line 16 from:
```javascript
const SERVER_URL = 'http://localhost:5001/flag';
```

To:
```javascript
const SERVER_URL = 'https://exam-monitor.onrender.com/flag';
// Replace 'exam-monitor' with your actual Render app name
```

**Edit `grid-dashboard.html`:**

Change line 312:
```javascript
const eventSource = new EventSource('http://localhost:5001/stream');
```

To:
```javascript
const eventSource = new EventSource('https://exam-monitor.onrender.com/stream');
```

Change lines 334, etc. (all fetch URLs):
```javascript
const response = await fetch('https://exam-monitor.onrender.com/live-screens');
```

**Reload extension:**
```
chrome://extensions/ → RELOAD button
```

---

## ✅ YOUR DEMO TOMORROW:

### What You'll Show:

**Dashboard:** https://exam-monitor.onrender.com/grid

**The Pitch:**
1. "This is running in the cloud - accessible from anywhere"
2. "IT deploys the extension via Group Policy"
3. "Proctors open this URL during exams"
4. "Watch what happens when someone tries to cheat..."

**The Demo:**
1. Open dashboard on big screen
2. Open ChatGPT on laptop (with extension)
3. Paste a question
4. 🚨 Instant alert with screenshot proof!

---

## 🎯 Demo Checklist:

Before your meeting:
- [ ] Code pushed to GitHub
- [ ] Deployed to Render
- [ ] Dashboard loads: https://your-app.onrender.com/grid
- [ ] Extension updated with production URL
- [ ] Extension reloaded in Chrome
- [ ] Test: Paste in ChatGPT → Alert appears
- [ ] Laptop charged
- [ ] HDMI cable ready

---

## 💡 Pro Tips:

**Render Free Tier:**
- ✅ Enough for demo
- ✅ SSL included (https)
- ⚠️ Spins down after 15 min of inactivity
- 💡 Open dashboard 5 min before demo to "wake it up"

**If Render is slow starting:**
- Open the dashboard URL 10 minutes before your demo
- First load might take 30 seconds (cold start)
- After that, it's instant

---

## 🔥 Alternative: Railway.app

If Render doesn't work:

1. Go to: https://railway.app
2. Sign up with GitHub
3. "New Project" → "Deploy from GitHub"
4. Select your repo
5. Railway auto-detects Python
6. Get URL, update extension
7. Done!

---

## 📱 For the Presentation:

**Opening:**
"I built an AI detection system for exam integrity. Let me show you how it works..."

**Live Demo:**
1. "This dashboard shows all students' screens in real-time"
2. "Every few seconds, updated screenshot - like security cameras"
3. **[Browse Google]** "See the live view?"
4. **[Go to ChatGPT]** "Now accessing ChatGPT..."
5. **[Paste text]** "And paste a question..."
6. **[🚨 ALERT!]** "Instant detection with screenshot proof!"

**The Close:**
"This costs $150/year vs. $10,000 for commercial tools. You already control the browsers via Group Policy - proved by the auto-tab feature. This plugs right in. Would you like to pilot it in one exam lab?"

---

## 🆘 Troubleshooting:

**"Extension can't connect to server":**
- Check URLs in background.js and grid-dashboard.html
- Make sure they match your Render URL
- Reload extension

**"Dashboard not loading":**
- Render free tier spins down - wait 30 seconds
- Check https:// (not http://)

**"No live updates":**
- Extension must be reloaded after URL change
- Check browser console for errors

---

## 📊 After the Demo:

If professor is interested:

**Phase 1 (Week 1):**
- Pilot in one exam lab
- 10-20 students
- Gather feedback

**Phase 2 (Week 2-3):**
- Add database (PostgreSQL on Render)
- Student ID integration
- Email alerts

**Phase 3 (Month 2):**
- Deploy school-wide
- IT training
- Policy updates

---

## 💰 Cost Breakdown for Production:

| Service | Cost |
|---------|------|
| Render Free Tier | $0/month |
| **OR** Render Pro | $7/month (if needed) |
| **OR** DigitalOcean | $5/month |
| Domain (optional) | $12/year |
| **Total** | **$0-84/year** |

Compare to commercial solutions: $10,000-50,000/year

---

## 🎉 You're Ready!

Your demo is production-ready. Deploy tonight, test once, and wow them tomorrow!

**Timeline:**
- Tonight: Deploy (10 min), test (5 min)
- Tomorrow: Practice demo (10 min), present (15 min)
- Result: Job offer or funding? 🚀

Good luck! 💪
