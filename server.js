const express = require("express");
const { request } = require("./gemini-request-manager.js");
const fs = require("fs");
const { spawn } = require("child_process");
const path = require("path");

const prompts = JSON.parse(fs.readFileSync("internal-prompts.json"));
const popularCities = JSON.parse(fs.readFileSync("popular-cities.json"));
const modelRunFile = "run_process.py";
const multiYearFile = "multi_year_run.py";

const app = express();
const port = 3000;

app.use(express.static("public"));

// --- Spawn persistent Python process (daily forecast) ---
const scriptPath = path.join(__dirname, modelRunFile);
const pythonProcess = spawn("python", [scriptPath]);

pythonProcess.stderr.on("data", (data) => {
  console.error("[Python STDERR]", data.toString());
});

function getWeatherPrediction(lat, lon, alt, date, city) {
  return new Promise((resolve, reject) => {
    const reqData = JSON.stringify({ lat, lon, alt, date, city });
    pythonProcess.stdin.write(reqData + "\n");

    pythonProcess.stdout.once("data", (data) => {
      try {
        const parsed = JSON.parse(data.toString());
        resolve(parsed);
      } catch (err) {
        reject(new Error("Invalid JSON from Python: " + data.toString()));
      }
    });
  });
}

// --- Spawn persistent Python process (multi-year) ---
const multiYearPath = path.join(__dirname, multiYearFile);
const multiYearProcess = spawn("python", [multiYearPath]);

multiYearProcess.stderr.on("data", (data) => {
  console.error("[Multi-Year STDERR]", data.toString());
});

function getMultiYearPrediction(lat, lon, alt, years, city, date) {
  return new Promise((resolve, reject) => {
    const reqData = JSON.stringify({ lat, lon, alt, years, city, date });
    console.log(reqData);
    multiYearProcess.stdin.write(reqData + "\n");

    multiYearProcess.stdout.once("data", (data) => {
      try {
        const parsed = JSON.parse(data.toString());
        resolve(parsed);
      } catch (err) {
        reject(
          new Error("Invalid JSON from Multi-Year Python: " + data.toString())
        );
      }
    });
  });
}

// --- Routes ---
app.listen(port, () => {
  console.log(`App listening on port ${port}`);
});

app.get("/get-advice", async (req, res) => {
  const weatherData = req.query.weather;
  const prompt = constructValues(
    prompts["Get advice for weather"],
    weatherData
  );
  const response = await request(prompt);
  res.send(response);
});

app.get("/get-history", async (req, res) => {
  const city = req.query.city;
  const date = req.query.date.slice(5);
  const prompt = constructValues(
    prompts["Get historical info for day"],
    date,
    city
  );
  const response = await request(prompt);
  res.send(response);
});

app.get("/get-report", async (req, res) => {
  const data = req.query.data;
  const prompt = constructValues(prompts["Generate report"], data);
  const response = await request(prompt);
  res.send(response);
});

app.get("/request-from-ai", async (req, res) => {
  let { city, date } = req.query;
  let lat, lon, alt;

  if (!popularCities[city.toLowerCase()]) {
    const prompt = constructValues(prompts["Coords from city name"], city);
    const results = await request(prompt);
    const coords = results.split(",");
    lat = coords[0];
    lon = coords[1];
    alt = coords[2];
  } else {
    lat = popularCities[city.toLowerCase()].latitude;
    lon = popularCities[city.toLowerCase()].longitude;
    alt = popularCities[city.toLowerCase()].elevation;
  }

  try {
    const prediction = await getWeatherPrediction(lat, lon, alt, date, city);
    res.json(prediction);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get("/multi-year-predict", async (req, res) => {
  let { city, years, date } = req.query;
  let lat, lon, alt;

  if (!popularCities[city.toLowerCase()]) {
    const prompt = constructValues(prompts["Coords from city name"], city);
    const results = await request(prompt);
    const coords = results.split(",");
    lat = coords[0];
    lon = coords[1];
    alt = coords[2];
  } else {
    lat = popularCities[city.toLowerCase()].latitude;
    lon = popularCities[city.toLowerCase()].longitude;
    alt = popularCities[city.toLowerCase()].elevation;
  }

  try {
    const prediction = await getMultiYearPrediction(
      lat,
      lon,
      alt,
      years,
      city,
      date
    );
    res.json(prediction);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// --- Utils ---
function constructValues(text = "", ...values) {
  for (let i = 0; i < values.length; i++) {
    text = text.replace(`##${i}##`, values[i]);
  }
  return text;
}
