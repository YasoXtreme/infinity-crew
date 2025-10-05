const { GoogleGenerativeAI } = require("@google/generative-ai");

const API_KEY = "AIzaSyBnJ9-5m3Z9MxoQOgd7PXCeiAVeHkSc3EA";

const genAI = new GoogleGenerativeAI(API_KEY);

async function request(prompt = "Tell me a fun fact about the Roman Empire.") {
  console.log("PROMPT:", prompt);
  try {
    const model = genAI.getGenerativeModel({ model: "gemini-flash-latest" });
    const result = await model.generateContent(prompt);

    const response = result.response;

    const text = response.text();
    console.log("GEMINI:", text);
    return text;
  } catch (error) {
    console.error("ERROR:", error);
    return "Sorry, I couldn't process that request.";
  }
}

module.exports = {
  request: request,
};
