function setupImageUpload(
    inputId,
    previewId,
    fileNameId,
    uploadAreaId
) {
    const input = document.getElementById(inputId);
    const preview = document.getElementById(previewId);
    const fileName = document.getElementById(fileNameId);
    const uploadArea = document.getElementById(uploadAreaId);

    if (!input || !preview || !fileName || !uploadArea) {
        return;
    }

    let previewUrl = null;

    input.addEventListener("change", function () {
        const file = input.files[0];

        if (previewUrl) {
            URL.revokeObjectURL(previewUrl);
            previewUrl = null;
        }

        if (!file) {
            preview.src = "";
            preview.style.display = "none";
            fileName.textContent = "";
            uploadArea.classList.remove("has-file");

            return;
        }

        previewUrl = URL.createObjectURL(file);

        preview.src = previewUrl;
        preview.style.display = "block";

        fileName.textContent = file.name;

        uploadArea.classList.add("has-file");
    });
}


setupImageUpload(
    "label-image",
    "primary-image-preview",
    "primary-file-name",
    "primary-upload-area"
);


setupImageUpload(
    "additional-label-image",
    "additional-image-preview",
    "additional-file-name",
    "additional-upload-area"
);
