/* ===============================
   RAZORPAY PRICING LOGIC
================================ */

function startPayment(plan, amount, isAuthenticated) {
    if (!requireLogin(isAuthenticated)) return;

    const options = {
        key: "rzp_test_RTcqfYh6IQHEOx", // Replace with your Razorpay key
        amount: amount * 100,
        currency: "INR",
        name: "CloudMS",
        description: `${plan} Plan Subscription`,
        handler: function (response) {
            alert("✅ Payment Successful");
            console.log("Payment ID:", response.razorpay_payment_id);
            window.location.href = "/dashboard/";
        },
        theme: {
            color: "#4f46e5"
        }
    };

    const rzp = new Razorpay(options);
    rzp.open();
}

/* ===============================
   PLAN BUTTON HANDLERS
================================ */
document.querySelectorAll(".plan-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        const plan = btn.dataset.plan;
        const amount = btn.dataset.amount;
        const isAuthenticated = btn.dataset.auth === "true";

        startPayment(plan, amount, isAuthenticated);
    });
});
