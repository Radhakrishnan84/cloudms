const fileInput = document.getElementById("fileInput");
const uploadList = document.getElementById("uploadList");
const folderSelect = document.getElementById("folderSelect");

// Handle browse button upload
fileInput.addEventListener("change", function () {
    uploadFiles(this.files);
});

// Handle drag-and-drop
const uploadBox = document.querySelector(".upload-box");

uploadBox.addEventListener("dragover", (e) => {
    e.preventDefault();
    uploadBox.classList.add("dragover");
});

uploadBox.addEventListener("dragleave", () => {
    uploadBox.classList.remove("dragover");
});

uploadBox.addEventListener("drop", (e) => {
    e.preventDefault();
    uploadBox.classList.remove("dragover");
    uploadFiles(e.dataTransfer.files);
});



// ---------------------------
// Upload Function (AJAX)
// ---------------------------
function uploadFiles(files) {
    [...files].forEach(file => uploadSingleFile(file));
}

function uploadSingleFile(file) {
    const folderId = folderSelect.value;

    // Create UI card
    const uploadId = "up_" + Math.random().toString(36).substr(2, 9);

    uploadList.insertAdjacentHTML("beforeend", `
        <div class="upload-item" id="${uploadId}">
            <div>
                <strong>${file.name}</strong>
                <div class="progress-bar">
                    <div class="progress"></div>
                </div>
            </div>
            <span class="status">0%</span>
        </div>
    `);

    const xhr = new XMLHttpRequest();
    const formData = new FormData();

    formData.append("file", file);
    formData.append("folder", folderId);
    formData.append("csrfmiddlewaretoken", "{{ csrf_token }}");

    xhr.upload.addEventListener("progress", function (e) {
        if (e.lengthComputable) {
            const percent = Math.round((e.loaded / e.total) * 100);
            const card = document.getElementById(uploadId);

            card.querySelector(".progress").style.width = percent + "%";
            card.querySelector(".status").innerText = percent + "%";

            if (percent === 100) {
                card.querySelector(".progress").style.background = "#28c76f"; // green on complete
            }
        }
    });

    xhr.onreadystatechange = function () {
        if (xhr.readyState === 4) {
            const card = document.getElementById(uploadId);

            if (xhr.status === 200) {
                card.querySelector(".status").innerText = "Uploaded";
            } else {
                card.querySelector(".progress").style.background = "red";
                card.querySelector(".status").innerText = "Failed";

                const response = JSON.parse(xhr.responseText);
                alert(response.error || "Upload failed");
            }
        }
    };

    xhr.open("POST", "{% url 'upload' %}");
    xhr.send(formData);
}
