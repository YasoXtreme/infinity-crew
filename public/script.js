let query = location.search;
let code = new URLSearchParams(query).get("x");
let x = parseInt(code.split(""));

if (x == 1) {
  document.getElementById("ground-normal").style.display = "inline";
  document.getElementById("cloud1").style.display = "inline";
  document.getElementById("cloud2").style.display = "inline";
  document.getElementById("cloud3").style.display = "inline";
  document.getElementById("cloud5").style.display = "inline";
  document.getElementById("sun-normal").style.display = "inline";
} else if (x == 2) {
  document.getElementById("ground-cold").style.display = "inline";
  document.getElementById("night-sky-cold").style.display = "inline";
} else if (x == 3) {
  document.getElementById("ground-cold").style.display = "inline";
  document.getElementById("night-sky-cold-rainy").style.display = "inline";
  document.getElementById("snow1").style.display = "inline";
  document.getElementById("snow2").style.display = "inline";
  document.getElementById("snow3").style.display = "inline";
  document.getElementById("snow4").style.display = "inline";
  document.getElementById("snow5").style.display = "inline";
  document.getElementById("snow6").style.display = "inline";
} else if (x == 4) {
  document.getElementById("hot-background").style.display = "inline";
  document.getElementById("boat").style.display = "inline";
  document.getElementById("ship").style.display = "inline";
  document.getElementById("thermo").style.display = "inline";
  document.getElementById("sun-hot").style.display = "inline";
} else if (x == 5) {
  document.getElementById("ground-rainy").style.display = "inline";
  document.getElementById("rainy-background").style.display = "inline";
  document.getElementById("rainy-clouds1").style.display = "inline";
  document.getElementById("rainy-clouds2").style.display = "inline";
  document.getElementById("rain1").style.display = "inline";
  document.getElementById("rain2").style.display = "inline";
  document.getElementById("rain3").style.display = "inline";
  document.getElementById("rain4").style.display = "inline";
  document.getElementById("rain5").style.display = "inline";
  document.getElementById("rain6").style.display = "inline";
  document.getElementById("rain7").style.display = "inline";
  document.getElementById("rain8").style.display = "inline";
  document.getElementById("rain9").style.display = "inline";
  document.getElementById("rain10").style.display = "inline";
  document.getElementById("rain11").style.display = "inline";
  document.getElementById("rain12").style.display = "inline";
  document.getElementById("rain13").style.display = "inline";
  document.getElementById("rain14").style.display = "inline";
  document.getElementById("rain15").style.display = "inline";
  document.getElementById("rain16").style.display = "inline";
  document.getElementById("rain17").style.display = "inline";
  document.getElementById("rain18").style.display = "inline";
  document.getElementById("rain19").style.display = "inline";
  document.getElementById("rain20").style.display = "inline";
} else if (x == 6) {
  document.getElementById("hot-cold-ground").style.display = "inline";
  document.getElementById("night-sky").style.display = "inline";
  document.getElementById("sun-hot-cold").style.display = "inline";
  document.getElementById("thermometer-hot").style.display = "inline";
  document.getElementById("thermometer-cold").style.display = "inline";
  document.getElementById("moon-hot-cold").style.display = "inline";
  document.getElementById("cloud-hot-cold1").style.display = "inline";
  document.getElementById("cloud-hot-cold2").style.display = "inline";
  document.getElementById("cloud-hot-cold3").style.display = "inline";
  document.getElementById("cloud-hot-cold4").style.display = "inline";
  document.getElementById("cloud-hot-cold5").style.display = "inline";
} else if (x == 7) {
  document.querySelector(".scene").style.display = "inline";
  document.querySelector(".cup").style.display = "inline";
  document.querySelector(".character").style.display = "inline";
  document.querySelector(".tree.left").style.display = "inline";
  document.querySelector(".tree.right").style.display = "inline";
  document.querySelector(".leaf").style.display = "inline";
  document.querySelector(".ground").style.display = "inline";
} else if (x == 8) {
  document.getElementbyId("Uncomfortable").style.display = "inline";
  
} else {
  alert("The weather data is unavailable");
}

const modal = document.getElementById("modal");
function openModal(title, body) {
  document.getElementById("modalTitle").innerText = title;
  document.getElementById("modalBody").innerText = body;
  modal.classList.add("active");
}
function closeModal() {
  modal.classList.remove("active");
}

const weatherIcons = ["⛅", "❄️", "⛄", "☀️", "🌧️", "🔥🧊", "💨", "😫"];

document.getElementById("icon").innerText = weatherIcons[x - 1];
document.getElementById("weatherText").innerText = decodeWeatherPhrase(code);

function createStars(count = 200) {
  const layer = document.getElementById("starsLayer");
  const w = window.innerWidth;
  const h = window.innerHeight;
  for (let i = 0; i < count; i++) {
    const s = document.createElement("div");
    s.className = "star";
    const size = Math.random() * 1.5 + 0.4;
    s.style.width = size + "px";
    s.style.height = size + "px";
    s.style.left = Math.random() * 100 + "vw";
    s.style.top = Math.random() * 100 + "vh";
    s.style.animationDuration = (Math.random() * 4 + 2).toFixed(1) + "s";
    s.style.animationDelay = (Math.random() * 4).toFixed(1) + "s";
    layer.appendChild(s);
  }
}
createStars(200);

function decodeWeatherPhrase(code) {
  const labelSets = {
    2: ["Chill", "Cold", "Very Cold", "Freezing"],
    3: {
      low: ["Chill", "Cold", "Very Cold", "Freezing"],
      rain: ["Drizzle", "Rain", "Heavy Rain", "Violent Rain"],
    },
    4: ["Warm", "Hot", "Very Hot", "Excessive Heat"],
    5: ["Drizzling", "Rainy", "Heavily Raining", "Violently Raining"],
    6: {
      high: ["Warm", "Hot", "Very Hot", "Excessive Heat"],
      low: ["Chill", "Cold", "Very Cold", "Freezing"],
    },
    7: ["Breezing", "Windy", "Very Windy", "Stormy"],
    8: ["Uneasy", "Uncomfortable", "Very Uncomfortable", "Overwhelming"],
  };

  const strCode = code.toString();
  const main = parseInt(strCode[0]);

  if (main === 1) return "Normal";
  if (main === 2) return labelSets[2][parseInt(strCode[1]) - 1];
  if (main === 3) {
    const low = labelSets[3].low[parseInt(strCode[1]) - 1];
    const rain = labelSets[3].rain[parseInt(strCode[2]) - 1];
    return `${low} ${rain}`;
  }
  if (main === 4) return labelSets[4][parseInt(strCode[1]) - 1];
  if (main === 5) return labelSets[5][parseInt(strCode[1]) - 1];
  if (main === 6) {
    const high = labelSets[6].high[parseInt(strCode[1]) - 1];
    const low = labelSets[6].low[parseInt(strCode[2]) - 1];
    return `${high} highs with ${low} lows`;
  }
  if (main === 7) return labelSets[7][parseInt(strCode[1]) - 1];
  if (main === 8) return labelSets[8][parseInt(strCode[1]) - 1];
}

function createShootingStar() {
  const shoot = document.createElement("div");
  shoot.className = "shoot";
  const startX = Math.random() * window.innerWidth * 0.7;
  const startY = Math.random() * window.innerHeight * 0.45;
  shoot.style.left = startX + "px";
  shoot.style.top = startY + "px";
  document.body.appendChild(shoot);

  const distanceX = Math.random() * 400 + 300;
  const distanceY = Math.random() * 200 + 200;
  shoot.animate(
    [
      { transform: "translate(0,0) rotate(-30deg)", opacity: 1 },
      {
        transform: `translate(${distanceX}px, ${distanceY}px) rotate(-30deg)`,
        opacity: 0,
      },
    ],
    {
      duration: 1500 + Math.random() * 800,
      easing: "cubic-bezier(.2,.8,.2,1)",
    }
  ).onfinish = () => shoot.remove();
}
setInterval(() => {
  if (Math.random() < 0.15) createShootingStar();
}, 1500);

/* ---------- Resize ---------- */
let resizeTimeout;
window.addEventListener("resize", () => {
  clearTimeout(resizeTimeout);
  resizeTimeout = setTimeout(() => {
    const layer = document.getElementById("starsLayer");
    layer.innerHTML = "";
    createStars(200);
  }, 250);
});

modal.addEventListener("click", (e) => {
  if (e.target === modal) closeModal();
});

async function makeAdviceModal() {
  openModal("💡 Advice", "Generating personalized advice...");
  const aiData = localStorage.getItem("ai-data");
  const response = await fetch(`/get-advice?weather=${aiData}`);
  const content = await response.text();

  openModal("💡 Advice", content);
}

async function makeHistoryModal() {
  openModal("History 📄", "Fetching historical details...");
  const city = localStorage.getItem("city");
  const date = localStorage.getItem("date");
  const response = await fetch(`/get-history?city=${city}&date=${date}`);
  const content = await response.text();

  openModal("History 📄", content);
}

function makeReport() {
  location.href = "/report.html";
}