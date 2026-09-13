/* =========================================================
   CAMPUSCARE - FINAL JAVASCRIPT
   ========================================================= */


/* =========================================================
   PASSWORD SHOW / HIDE
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    const passwordToggles = document.querySelectorAll(".password-toggle");

    passwordToggles.forEach(function (toggle) {

        toggle.addEventListener("click", function () {

            const wrapper = toggle.closest(".password-wrapper");

            if (!wrapper) return;

            const input = wrapper.querySelector("input");

            if (!input) return;

            if (input.type === "password") {
                input.type = "text";
                toggle.textContent = "🙈";
            } else {
                input.type = "password";
                toggle.textContent = "👁";
            }

        });

    });


    /* =====================================================
       FILE UPLOAD
       ===================================================== */

    const fileInput = document.getElementById("attachment");
    const fileName = document.getElementById("fileName");

    if (fileInput) {

        fileInput.addEventListener("change", function () {

            if (!this.files || this.files.length === 0) {
                if (fileName) {
                    fileName.textContent = "";
                }
                return;
            }

            const file = this.files[0];

            const maxSize = 100 * 1024 * 1024;

            if (file.size > maxSize) {

                alert("File size must be less than 100 MB.");

                this.value = "";

                if (fileName) {
                    fileName.textContent = "";
                }

                return;
            }

            if (fileName) {
                fileName.textContent = "Selected: " + file.name;
            }

        });

    }


    /* =====================================================
       COMPLAINT FORM VALIDATION
       ===================================================== */

    const complaintForm = document.getElementById("complaintForm");

    if (complaintForm) {

        complaintForm.addEventListener("submit", function (event) {

            const studentClass =
                document.getElementById("student_class");

            const category =
                document.getElementById("category");

            const subject =
                document.getElementById("subject");

            const description =
                document.getElementById("description");

            if (studentClass && studentClass.value.trim() === "") {

                event.preventDefault();

                alert("Please enter your Class / Section.");

                studentClass.focus();

                return;
            }

            if (category && category.value === "") {

                event.preventDefault();

                alert("Please select a complaint category.");

                category.focus();

                return;
            }

            if (subject && subject.value.trim() === "") {

                event.preventDefault();

                alert("Please enter complaint subject.");

                subject.focus();

                return;
            }

            if (description && description.value.trim() === "") {

                event.preventDefault();

                alert("Please describe your complaint.");

                description.focus();

                return;
            }

        });

    }


    /* =====================================================
       FLASH MESSAGE AUTO HIDE
       ===================================================== */

    const flashMessages =
        document.querySelectorAll(".flash-message");

    flashMessages.forEach(function (message) {

        setTimeout(function () {

            message.style.opacity = "0";

            message.style.transform = "translateY(-5px)";

            message.style.transition = "0.4s";

            setTimeout(function () {
                message.remove();
            }, 400);

        }, 5000);

    });


    /* =====================================================
       STATUS UPDATE CONFIRMATION
       ===================================================== */

    const statusForms =
        document.querySelectorAll(".status-form");

    statusForms.forEach(function (form) {

        form.addEventListener("submit", function (event) {

            const select = form.querySelector("select");

            if (!select) return;

            const newStatus = select.value;

            const confirmed =
                confirm(
                    "Are you sure you want to change the complaint status to " +
                    newStatus +
                    "?"
                );

            if (!confirmed) {
                event.preventDefault();
            }

        });

    });

});


/* =========================================================
   USE MY LOCATION
   ========================================================= */

function getLocation() {

    const locationInput =
        document.getElementById("location");

    if (!locationInput) return;


    if (!navigator.geolocation) {

        alert(
            "Geolocation is not supported by your browser."
        );

        return;
    }


    locationInput.value = "Getting your location...";


    navigator.geolocation.getCurrentPosition(

        function (position) {

            const latitude =
                position.coords.latitude.toFixed(6);

            const longitude =
                position.coords.longitude.toFixed(6);


            locationInput.value =
                "Latitude: " +
                latitude +
                ", Longitude: " +
                longitude;

        },

        function (error) {

            locationInput.value = "";

            if (error.code === 1) {

                alert(
                    "Location permission was denied. Please allow location access."
                );

            } else {

                alert(
                    "Unable to get your current location."
                );

            }

        },

        {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 0
        }

    );

}


/* =========================================================
   CAMERA SYSTEM
   ========================================================= */

let campusCameraStream = null;


/* OPEN CAMERA */

async function openCamera() {

    const cameraContainer =
        document.getElementById("cameraContainer");

    const video =
        document.getElementById("cameraVideo");

    if (!cameraContainer || !video) return;


    try {

        campusCameraStream =
            await navigator.mediaDevices.getUserMedia({
                video: true,
                audio: false
            });


        video.srcObject = campusCameraStream;

        cameraContainer.style.display = "block";

    } catch (error) {

        alert(
            "Camera access denied or unavailable. Please allow camera permission."
        );

    }

}


/* CAPTURE CAMERA IMAGE */

function capturePhoto() {

    const video =
        document.getElementById("cameraVideo");

    const canvas =
        document.getElementById("cameraCanvas");

    const preview =
        document.getElementById("cameraPreview");

    const fileInput =
        document.getElementById("attachment");

    if (!video || !canvas || !preview || !fileInput) {
        return;
    }


    if (
        video.videoWidth === 0 ||
        video.videoHeight === 0
    ) {

        alert(
            "Camera is not ready yet. Please wait for the camera preview."
        );

        return;
    }


    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;


    const context =
        canvas.getContext("2d");

    context.drawImage(
        video,
        0,
        0,
        canvas.width,
        canvas.height
    );


    canvas.toBlob(function (blob) {

        if (!blob) return;


        const capturedFile =
            new File(
                [blob],
                "campuscare-camera-evidence.jpg",
                {
                    type: "image/jpeg"
                }
            );


        try {

            const dataTransfer =
                new DataTransfer();

            dataTransfer.items.add(capturedFile);

            fileInput.files =
                dataTransfer.files;

        } catch (error) {

            console.log(
                "Unable to attach captured image automatically.",
                error
            );

        }


        preview.innerHTML = "";

        const image =
            document.createElement("img");

        image.src =
            URL.createObjectURL(blob);

        image.alt =
            "Captured complaint evidence";

        preview.appendChild(image);


        const fileName =
            document.getElementById("fileName");

        if (fileName) {

            fileName.textContent =
                "Camera photo captured: campuscare-camera-evidence.jpg";

        }

    }, "image/jpeg", 0.92);

}


/* CLOSE CAMERA */

function closeCamera() {

    const cameraContainer =
        document.getElementById("cameraContainer");

    const video =
        document.getElementById("cameraVideo");


    if (campusCameraStream) {

        campusCameraStream
            .getTracks()
            .forEach(function (track) {
                track.stop();
            });

        campusCameraStream = null;

    }


    if (video) {
        video.srcObject = null;
    }


    if (cameraContainer) {
        cameraContainer.style.display = "none";
    }

}


/* =========================================================
   STOP CAMERA WHEN PAGE IS CLOSED
   ========================================================= */

window.addEventListener("beforeunload", function () {

    if (campusCameraStream) {

        campusCameraStream
            .getTracks()
            .forEach(function (track) {
                track.stop();
            });

        campusCameraStream = null;

    }

});