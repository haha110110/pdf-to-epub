import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import EditorPage from './pages/EditorPage';

import ProjectsList from './pages/ProjectsList';

function App() {
    return (
        <Router>
            <div className="min-h-screen bg-gray-50 text-gray-900 font-sans">
                <Routes>
                    <Route path="/" element={<Home />} />
                    <Route path="/projects" element={<ProjectsList />} />
                    <Route path="/editor/:projectId" element={<EditorPage />} />
                </Routes>
            </div>
        </Router>
    );
}

export default App;
