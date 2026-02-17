const fileInput = document.getElementById("fileInput");
const uploadList = document.getElementById("uploadList");
const folderSelect = document.getElementById("folderSelect");

fileInput.addEventListener("change", () => {
    [...fileInput.files].forEach(file => startUpload(file));
});

function startUpload(file) {
    const row = document.createElement("div");
    row.className = "upload-row";

    row.innerHTML = `
        <div>${file.name}</div>
        <progress max="100" value="0"></progress>
        <span class="status">Uploading...</span>
        <button class="cancel">✖</button>
    `;

    uploadList.appendChild(row);

    const progressBar = row.querySelector("progress");
    const statusText = row.querySelector(".status");
    const cancelBtn = row.querySelector(".cancel");

    const xhr = new XMLHttpRequest();
    const formData = new FormData();

    formData.append("file", file);
    formData.append("folder", folderSelect.value);

    xhr.open("POST", "/upload/", true);

    // CSRF
    xhr.setRequestHeader(
        "X-CSRFToken",
        getCookie("csrftoken")
    );

    xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
            progressBar.value = (e.loaded / e.total) * 100;
        }
    };

    xhr.onload = () => {
        if (xhr.status === 200) {
            statusText.textContent = "Uploaded ✅";
        } else {
            statusText.textContent = "Failed ❌";
        }
    };

    xhr.onerror = () => {
        statusText.textContent = "Failed ❌";
    };

    cancelBtn.onclick = () => {
        xhr.abort();
        statusText.textContent = "Cancelled";
    };

    xhr.send(formData);
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
        document.cookie.split(";").forEach(cookie => {
            cookie = cookie.trim();
            if (cookie.startsWith(name + "=")) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
            }
        });
    }
    return cookieValue;
}
