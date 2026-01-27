// Firebase configuration for Alertrix
import { initializeApp } from 'firebase/app';
import { getAuth, GoogleAuthProvider } from 'firebase/auth';

const firebaseConfig = {
    apiKey: "AIzaSyD2MwXCv3J4hJ1wqvgxODeSBqv2RFyI-BA",
    authDomain: "alertrix-5450f.firebaseapp.com",
    projectId: "alertrix-5450f",
    storageBucket: "alertrix-5450f.firebasestorage.app",
    messagingSenderId: "1013984879728",
    appId: "1:1013984879728:web:59c4b1ced6eef7d50a00b5",
    measurementId: "G-M3K1287YZP"
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();

export default app;
