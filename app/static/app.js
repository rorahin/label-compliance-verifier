const fileInput = document.getElementById("label-image");
const preview = document.getElementById("image-preview");

fileInput.addEventListener("change", function () {
    const file = fileInput.files[0];

    if (!file) {
        preview.style.display = "none";
        preview.src = "";
        return;
    }

    preview.src = URL.createObjectURL(file);
    preview.style.display = "block";
});
