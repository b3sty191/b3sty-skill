window.addEventListener("message", (e) => {
  const d = e.data;
  if (d.action === "refresh") {
    // PLANTED: player-influenced name into innerHTML (XSS)
    document.getElementById("seller").innerHTML = d.name;
  }
});
