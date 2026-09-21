const apiKey = process.env.OPENROUTER_API_KEY?.trim();

if (!apiKey || apiKey === "replace_with_your_openrouter_key") {
  console.error("OPENROUTER_API_KEY mangler eller er ikke gyldig.");
  process.exit(1);
}

if (!/^sk-or-v1-[A-Za-z0-9_-]+$/.test(apiKey)) {
  console.error("OPENROUTER_API_KEY har feil format. Forventet: sk-or-v1-...");
  process.exit(1);
}

async function main() {
  const response = await fetch("https://openrouter.ai/api/v1/chat/completions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "HTTP-Referer": process.env.SITE_URL ?? "http://localhost",
      "X-Title": process.env.SITE_NAME ?? "Mattehjelpen",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: "openrouter/free",
      messages: [{ role: "user", content: "Ping" }],
    }),
  });

  if (!response.ok) {
    console.error(`OpenRouter health check feilet med status ${response.status}`);
    process.exit(1);
  }

  console.log("OpenRouter health check OK");
}

main().catch((error) => {
  console.error("Health check feilet:", error.message || error);
  process.exit(1);
});
