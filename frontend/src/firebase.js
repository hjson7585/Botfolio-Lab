import { initializeApp }
from "firebase/app";

import {
    getAuth,
    GoogleAuthProvider
}
from "firebase/auth";

import {
    getFirestore
}
from "firebase/firestore";


const firebaseConfig = {

    apiKey: "AIzaSyBfGu0XK4145qD8ZFKiH_Ag0bPqRmUsesQ",

    authDomain: "botfolio-lab-9040c.firebaseapp.com",

    projectId: "botfolio-lab-9040c",

    storageBucket: "botfolio-lab-9040c.firebasestorage.app",

    messagingSenderId:
        "733700954947",

    appId: "1:733700954947:web:c53cf2c682a3a45196edf6"
};


// Firebase 앱 초기화
const app = initializeApp(
    firebaseConfig
);


// Firebase Auth
export const auth =
    getAuth(app);


// Google Provider
export const provider =
    new GoogleAuthProvider();


// Firestore DB
export const db =
    getFirestore(app);
