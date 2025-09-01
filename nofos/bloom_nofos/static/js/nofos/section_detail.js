document.addEventListener("DOMContentLoaded", () => {
  // Set CSS var to current table width (for Safari button positioning)
  const setTableWidthVariable = () => {
    const table = document.querySelector("table.table--section");
    if (table) {
      document.documentElement.style.setProperty(
        "--safari-tr-width",
        table.offsetWidth + "px"
      );
    }
  };

  // Initial run
  setTableWidthVariable();

  // Debounced resize
  let t;
  window.addEventListener("resize", () => {
    clearTimeout(t);
    t = setTimeout(setTableWidthVariable, 200);
  });
});
