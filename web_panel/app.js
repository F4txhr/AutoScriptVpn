const toggleButton = document.getElementById("toggleSidebar");
const sidebar = document.getElementById("sidebar");

toggleButton.addEventListener("click", () => {
  sidebar.classList.toggle("open");
});

const stats = {
  nodes: 6,
  users: 148,
  traffic: "1.2 TB",
  alerts: 2,
};

document.querySelectorAll("[data-value]").forEach((element) => {
  const key = element.dataset.value;
  if (stats[key]) {
    element.textContent = stats[key];
  }
});
