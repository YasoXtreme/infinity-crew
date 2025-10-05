const cityInput = document.getElementById("city");
const dateInput = document.getElementById("date");
const submitButton = document.getElementById("submit-button");
const loading = document.getElementById("loading")
const bottom = document.getElementsByClassName ("")

submitButton.addEventListener("click", async () => {
  const city = cityInput.value;
  const date = dateInput.value;

  console.log(loading)
  loading.style.display = 'inline-block';
  submitButton.disabled= true;
  submitButton.color = '#0571d3';
  submitButton.height = '50';

  const response = await fetch(`/request-from-ai?city=${city}&date=${date}`);
  const prediction = await response.json();
  console.log(prediction);

  let x = findWeatherCodeFromProbs(prediction.likelihoods);
  console.log(x);

  localStorage.setItem("ai-data", JSON.stringify(prediction));
  localStorage.setItem("date", dateInput.value);
  localStorage.setItem("city", cityInput.value);
  location.href = `main.html?x=${x}`;
});

function findWeatherCodeFromProbs(probs) {
  const thresholds = [15, 30, 50, 80];

  function tier(prob) {
    if (prob >= thresholds[3]) return 4;
    if (prob >= thresholds[2]) return 3;
    if (prob >= thresholds[1]) return 2;
    if (prob >= thresholds[0]) return 1;
    return 0;
  }

  const tempHighTier = tier(probs["Very Hot"]);
  const tempLowTier = tier(probs["Very Cold"]);
  const rainTier = tier(probs["Very Rainy"]);
  const windTier = tier(probs["Very Windy"]);
  const discomfortTier = tier(probs["Very Uncomfortable"]);

  // Apply rules in order of specificity
  if (tempHighTier && tempLowTier)
    return parseInt(`6${tempHighTier}${tempLowTier}`);
  if (tempLowTier && rainTier) return parseInt(`3${tempLowTier}${rainTier}`);
  if (tempLowTier) return parseInt(`2${tempLowTier}`);
  if (tempHighTier) return parseInt(`4${tempHighTier}`);
  if (rainTier) return parseInt(`5${rainTier}`);
  if (windTier) return parseInt(`7${windTier}`);
  if (discomfortTier) return parseInt(`8${discomfortTier}`);

  return 1; // Normal
}
