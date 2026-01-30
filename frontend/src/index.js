import React from 'react';
import ReactDOM from 'react-dom/client';
import { GoogleOAuthProvider } from '@react-oauth/google';
import './App.css';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));

const CLIENT_ID = '552040332292-c67tnmsqf3iog66c5ur23evqjevnamcq.apps.googleusercontent.com';

root.render(
  <React.StrictMode>
    <GoogleOAuthProvider clientId={CLIENT_ID}>
      <App />
    </GoogleOAuthProvider>
  </React.StrictMode>
);

