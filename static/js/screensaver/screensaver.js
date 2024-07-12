let spd = 125;
let ratio_aspect = 0.2; // Image ratio_aspect (I work on 1080p monitor)
let canvas;
let ctx;
let logoColor;

let TAD = {
    x: 20,
    y: 30,
    xspd: 10,
    yspd: 10,
    img: new Image()
};

(function main() {
    canvas = document.getElementById("tv-screen");
    ctx = canvas.getContext("2d");
    console.log("Canvas loaded");
    TAD.img.src = '/static/images/image.png';
    //Draw the "tv screen"
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    // pickColor();
    update();
})();

function update() {
    setTimeout(() => {
        //Draw the canvas background
        ctx.fillStyle = '#000';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        //Draw TAD Logo and his background
        ctx.fillStyle = 'rgb(0, 0, 0)';
        ctx.fillRect(TAD.x, TAD.y, TAD.img.width * ratio_aspect, TAD.img.height * ratio_aspect);
        ctx.drawImage(TAD.img, TAD.x, TAD.y, TAD.img.width * ratio_aspect, TAD.img.height * ratio_aspect);
        //Move the logo
        TAD.x += TAD.xspd;
        TAD.y += TAD.yspd;
        //Check for collision 
        checkHitBox();
        update();
    }, spd)
}

//Check for border collision
function checkHitBox() {
    if (TAD.x + TAD.img.width * ratio_aspect >= canvas.width || TAD.x <= 0) {
        TAD.xspd *= -1;
        // pickColor();
    }

    if (TAD.y + TAD.img.height * ratio_aspect >= canvas.height || TAD.y <= 0) {
        TAD.yspd *= -1;
        // pickColor();
    }
}