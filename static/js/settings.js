// ===============================
// SETTINGS PAGE JS WORKFLOW
// ===============================

// ------- CSRF Token Helper -------
function getCSRFToken() {
    let cookieValue = null;
    let cookies = document.cookie.split(";");

    for (let c of cookies) {
        let cookie = c.trim();
        if (cookie.startsWith("csrftoken=")) {
            cookieValue = cookie.substring("csrftoken=".length);
        }
    }
    return cookieValue;
}

const csrfToken = getCSRFToken();


// ======================================
// 1️⃣ PROFILE PHOTO UPLOAD LIVE PREVIEW
// ======================================
const photoInput = document.getElementById("photoInput");
const previewImg = document.getElementById("profilePreview");
const uploadForm = document.getElementById("photoUploadForm");

if (photoInput) {
    photoInput.addEventListener("change", function () {
        let file = this.files[0];
        if (!file) return;

        // Preview image
        previewImg.src = URL.createObjectURL(file);

        // Auto-submit upload
        uploadForm.submit();
    });
}


// ======================================
// 2️⃣ REMOVE PROFILE PHOTO
// ======================================
const removeBtn = document.getElementById("removePhotoBtn");
const removeForm = document.getElementById("removePhotoForm");

if (removeBtn && removeForm) {
    removeBtn.addEventListener("click", () => {
        if (confirm("Remove profile photo?")) {
            removeForm.submit();
        }
    });
}


// ======================================
// 3️⃣ SAVE PROFILE FORM (Name / Email)
// ======================================
const saveBtn = document.getElementById("saveProfileBtn");
const profileForm = document.getElementById("profileForm");

if (saveBtn && profileForm) {
    saveBtn.addEventListener("click", () => {
        profileForm.submit();
    });
}


// ======================================
// 4️⃣ PREFERENCES (Toggle Switches)
// Auto-save on toggle
// ======================================
function autoSaveToggle(fieldName, value) {
    fetch("/settings/", {
        method: "POST",
        headers: {
            "X-CSRFToken": csrfToken,
            "X-Requested-With": "XMLHttpRequest",
        },
        body: new URLSearchParams({
            preferences: "1",
            [fieldName]: value ? "on" : "",
        }),
    }).then(res => {
        console.log(fieldName + " updated");
    });
}

const darkToggle = document.getElementById("darkModeToggle");
const notifyToggle = document.getElementById("emailNotifyToggle");
const autosyncToggle = document.getElementById("autosyncToggle");

if (darkToggle) {
    darkToggle.addEventListener("change", () => {
        autoSaveToggle("dark_mode", darkToggle.checked);
    });
}

if (notifyToggle) {
    notifyToggle.addEventListener("change", () => {
        autoSaveToggle("email_notify", notifyToggle.checked);
    });
}

if (autosyncToggle) {
    autosyncToggle.addEventListener("change", () => {
        autoSaveToggle("autosync", autosyncToggle.checked);
    });
}
