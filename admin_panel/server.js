const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');
const csv = require('csv-parser');
const { createProxyMiddleware } = require('http-proxy-middleware');

const app = express();
const PORT = 8503; // Accessible port

// API Proxy for AI Chatbot (FastAPI on Port 8000)
// Using array filter and no path in app.use to ensure the path is forwarded correctly
app.use(createProxyMiddleware(
    (path, req) => ['/api/chat', '/api/lead', '/api/voice-chat'].includes(path),
    {
        target: 'http://localhost:8000',
        changeOrigin: true
    }
));

// Middleware
app.use(cors());
app.use(express.static(__dirname)); // Serve HTML files

// Path to leads CSV (one level up in the data folder)
const csvFilePath = path.join(__dirname, '..', 'data', 'leads.csv');

// Endpoints

// 1. Get all leads as JSON for dashboard
app.get('/api/leads', (req, res) => {
    const results = [];

    if (!fs.existsSync(csvFilePath)) {
        return res.json([]); // Return empty if file doesnt exist
    }

    fs.createReadStream(csvFilePath)
        .pipe(csv())
        .on('data', (data) => results.push(data))
        .on('end', () => {
            res.json(results);
        })
        .on('error', (err) => {
            console.error("Error reading CSV:", err);
            res.status(500).send("Error reading data");
        });
});

// 2. Download raw CSV file
app.get('/api/download-csv', (req, res) => {
    if (fs.existsSync(csvFilePath)) {
        res.setHeader('Content-disposition', 'attachment; filename=svsu_leads_export.csv');
        res.setHeader('Content-type', 'text/csv');
        fs.createReadStream(csvFilePath).pipe(res);
    } else {
        res.status(404).send('No data found');
    }
});

// Serve Main Chatbot Landing Page
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'chatbot.html'));
});

// Admin Login
app.get('/admin', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

// Admin Dashboard
app.get('/dashboard', (req, res) => {
    res.sendFile(path.join(__dirname, 'dashboard.html'));
});


app.listen(PORT, () => {
    console.log(`🚀 SVSU Admin Panel running at http://localhost:${PORT}`);
    console.log(`📡 Serving data from ${csvFilePath}`);
});
