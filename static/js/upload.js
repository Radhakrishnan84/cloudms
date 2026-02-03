const fileInput = document.getElementById("fileInput");
const uploadList = document.getElementById("uploadList");
const folderSelect = document.getElementById("folderSelect");

fileInput.addEventListener("change", () => {
    [...fileInput.files].forEach(uploadFile);
});

function uploadFile(file) {
    const row = document.createElement("div");
    row.className = "upload-row";

    row.innerHTML = `
        <div>${file.name}</div>
        <div class="progress-bar"><div class="progress-fill"></div></div>
        <div class="status">Uploading...</div>
        <button class="cancel-btn">✖</button>
    `;

    uploadList.appendChild(row);

    const progressFill = row.querySelector(".progress-fill");
    const statusText = row.querySelector(".status");
    const cancelBtn = row.querySelector(".cancel-btn");

    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append("file", file);
    formData.append("folder", folderSelect.value);

    xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
            progressFill.style.width = (e.loaded / e.total) * 100 + "%";
        }
    };

    xhr.onload = () => {
        if (xhr.status === 200) {
            statusText.innerText = "Uploaded ✔";
            updateStorage();
        } else {
            showRetry();
        }
    };

    xhr.onerror = showRetry;

    function showRetry() {
        statusText.innerText = "Failed ❌";
        const retry = document.createElement("button");
        retry.innerText = "Retry";
        retry.className = "retry-btn";
        retry.onclick = () => {
            row.remove();
            uploadFile(file);
        };
        row.appendChild(retry);
    }

    cancelBtn.onclick = () => {
        xhr.abort();
        statusText.innerText = "Cancelled";
        progressFill.style.background = "gray";
    };

    xhr.open("POST", "/upload/");
    xhr.setRequestHeader("X-CSRFToken", getCSRFToken());
    xhr.send(formData);
}

function updateStorage() {
    fetch("/storage-status/")
        .then(res => res.json())
        .then(data => {
            document.querySelector(".fill").style.width = data.percent + "%";
            document.querySelector(".small").innerText =
                `${data.used} GB of ${data.total} GB used`;
        });
}

function getCSRFToken() {
    return document.cookie.split("; ")
        .find(row => row.startsWith("csrftoken"))
        ?.split("=")[1];
}
