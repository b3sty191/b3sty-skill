window.addEventListener("message", (e) => {
  const d = e.data;
  if (d.action === "refresh") {
    document.getElementById("last-buyer").innerHTML = d.lastBuyer;
  }
});
