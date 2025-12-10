# 🚀 QUICK START - Get Your Demo Running NOW!

## Step 1: Install Flask (30 seconds)

Open terminal and run:

```bash
pip3 install flask flask-cors --break-system-packages
```

**OR** if you get an error:

```bash
python3 -m pip install flask flask-cors --break-system-packages
```

---

## Step 2: Start the Dashboard (10 seconds)

```bash
cd /Users/admin/Downloads/exama/exam-monitor
python3 server.py
```

You should see:
```
🚀 EXAM INTEGRITY MONITOR SERVER
📊 Dashboard: http://localhost:5000/dashboard
```

**Keep this terminal open!** The server needs to run.

---

## Step 3: Load Extension in Chrome (1 minute)

1. Open **Chrome** browser
2. Type in address bar: `chrome://extensions/`
3. Turn ON **"Developer mode"** (toggle switch, top-right corner)
4. Click the **"Load unpacked"** button
5. Navigate to and select this folder:
   `/Users/admin/Downloads/exama/exam-monitor`
6. Click "Select" or "Open"

You should see "Exam Integrity Monitor" in your extensions list! ✅

---

## Step 4: Test It! (30 seconds)

### Open Two Windows Side-by-Side:

**Window 1 (Left side):**
- Go to: http://localhost:5000/dashboard
- This is your supervisor view

**Window 2 (Right side):**
- Go to: https://chatgpt.com
- Or try: https://claude.ai

### What Should Happen:

**INSTANTLY** you'll see:
- 🚨 Alert appears on the dashboard (Window 1)
- Red flag with student ID
- Screenshot of the violation
- Exact timestamp

---

## 🎬 Demo Script for Your Presentation

### The Setup:
- MacBook with two browser windows visible
- Left: Dashboard showing "No violations"
- Right: Regular browser on Google.com

### The Demo (20 seconds):

1. **Point to dashboard:** "This is what supervisors see during exams"

2. **Switch to browser:** "Here's a student taking an exam..."

3. **Type "chatgpt.com"** and press Enter

4. **BOOM! Point to dashboard:**
   - "Look - instant alert!"
   - "Student ID, timestamp, screenshot"
   - "Even if they close it immediately, we caught it"

5. **The Closer:**
   "Your IT department already controls these browsers - remember the Saint Clair tab that auto-opens? This deploys the exact same way through Group Policy. No new infrastructure, just adding eyes to exam integrity."

---

## 🎯 Key Demo Talking Points

✅ **"Works on Chrome AND Edge"** - Same extension, both browsers (Edge is Chromium)

✅ **"Students can't disable it"** - Admin-enforced, just like your auto-tab

✅ **"Real-time, not after the fact"** - Catch them in the act, not days later

✅ **"Screenshot proof"** - Not just logs, visual evidence

✅ **"Scales to entire lab"** - One dashboard monitors 50+ students

✅ **"Plugs into existing systems"** - Uses infrastructure you already have

---

## 🔥 Advanced Demo Tricks

### Test Multiple Sites:
- https://chatgpt.com
- https://claude.ai
- https://gemini.google.com
- https://copilot.microsoft.com

Each one triggers a new alert instantly!

### Show the Popup:
- Click the blue extension icon (top-right in Chrome)
- Shows "Exam Monitor Active" status
- Point out: "Student sees this, knows they're monitored"

### Auto-Refresh:
- The dashboard auto-refreshes every 3 seconds
- New flags appear without clicking anything
- Show them this is truly "live"

---

## ❓ Troubleshooting

**"Module not found: flask"**
- Run the pip install command again
- Make sure you're using `pip3` not just `pip`

**"Extension didn't load"**
- Make sure you selected the `/exam-monitor` folder itself
- All files should be in ONE folder together
- Check Developer Mode is ON

**"No alerts appearing"**
- Check the server is running (terminal should show activity)
- Try opening http://localhost:5000/ first
- Look for errors in Chrome DevTools Console

**"Screenshot not showing"**
- Some sites block screenshots (browser security)
- URL and timestamp still captured perfectly

---

## 📊 What Happens Next?

After your demo, if Saint Clair is interested:

### Phase 1: Pilot Program (2-4 weeks)
- Install in one exam lab
- Test with real students (tell them it's there)
- Collect feedback from proctors
- Refine the blocked site list

### Phase 2: Production Deployment
- IT pushes via Group Policy
- Deploy to all exam labs
- Add database for permanent storage
- Integrate with student ID system

### Phase 3: Advanced Features
- Export reports (PDF/CSV)
- Email alerts for supervisors
- Mobile app for admins
- Analytics dashboard

---

## 🎓 The Pitch

**"You already have everything you need to deploy this. Your IT controls the browsers, your exam labs are ready, and your students expect monitoring during exams. We're just making it impossible to cheat with AI - which is your biggest threat right now."**

---

## 📞 Ready to Present?

Checklist before you walk into that meeting:

- [ ] Server runs without errors
- [ ] Dashboard loads and looks professional
- [ ] Extension is loaded in Chrome
- [ ] You've tested it successfully 2-3 times
- [ ] You can explain "admin deployment" confidently
- [ ] Laptop is charged! 🔋

---

**You're ready to blow their minds! 🚀**

Show them cheating is impossible when you have eyes on every tab.
