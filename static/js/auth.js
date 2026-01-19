/* ===============================
   LOGIN REQUIRED CHECK
================================ */
function requireLogin(isAuthenticated) {
    if (!isAuthenticated) {
        alert("⚠️ Please login first to continue");
        window.location.href = "/login/";
        return false;
    }
    return true;
}
