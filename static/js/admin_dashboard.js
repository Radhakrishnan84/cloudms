// USER ACTIVITY
new Chart(document.getElementById("userActivityChart"), {
    type: "line",
    data: {
        labels: ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"],
        datasets: [{
            label: "Users",
            data: [4000,3500,2500,1800,1600,3200,3900],
            fill: true,
            borderColor: "#7b3df0",
            backgroundColor: "rgba(123, 61, 240, 0.2)",
            tension: 0.4
        }]
    }
});


// PLAN DISTRIBUTION
new Chart(document.getElementById("planChart"), {
    type: "doughnut",
    data: {
        labels: ["Free", "Basic", "Pro", "Enterprise"],
        datasets: [{
            data: [6800,3200,1800,743],
            backgroundColor: ["#ccc","#7b3df0","#3db5ff","#ffd233"]
        }]
    }
});


// STORAGE GROWTH
new Chart(document.getElementById("storageChart"), {
    type: "bar",
    data: {
        labels: ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug"],
        datasets: [{
            label: "TB",
            data: [3,4,3.5,5,7,8,10,12],
            backgroundColor: "#7b3df0"
        }]
    }
});
