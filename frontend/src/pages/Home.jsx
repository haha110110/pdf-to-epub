import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, FileText, Loader2 } from 'lucide-react';
import { uploadPDF } from '../api';

import { Link } from 'react-router-dom';

const Home = () => {
    const navigate = useNavigate();
    const [isUploading, setIsUploading] = useState(false);

    const handleFileChange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        setIsUploading(true);
        const formData = new FormData();
        formData.append('file', file);

        try {
            const { data } = await uploadPDF(formData);
            // Navigate to editor with the new project ID
            navigate(`/editor/${data.project_id}`);
        } catch (error) {
            console.error("Upload failed", error);
            alert("Failed to upload PDF");
        } finally {
            setIsUploading(false);
        }
    };

    return (
        <div className="flex flex-col items-center justify-center min-h-screen p-4 relative">
            <div className="absolute top-6 right-6">
                <Link to="/projects" className="text-gray-600 hover:text-indigo-600 font-medium flex items-center gap-2">
                    <FileText className="w-5 h-5" />
                    My Projects
                </Link>
            </div>

            <div className="max-w-2xl w-full text-center space-y-8">
                <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-6xl">
                    PDF to Smart EPUB
                </h1>
                <p className="text-lg leading-8 text-gray-600">
                    Convert academic PDFs to mobile-friendly EPUBs with smart image relocation.
                </p>

                <div className="mt-10 flex items-center justify-center gap-x-6">
                    <label className="relative cursor-pointer group">
                        <input
                            type="file"
                            className="hidden"
                            accept=".pdf"
                            onChange={handleFileChange}
                            disabled={isUploading}
                        />
                        <div className="flex items-center gap-3 px-8 py-4 bg-indigo-600 text-white rounded-xl shadow-lg hover:bg-indigo-500 transition-all transform hover:scale-105 active:scale-95">
                            {isUploading ? (
                                <Loader2 className="w-6 h-6 animate-spin" />
                            ) : (
                                <Upload className="w-6 h-6" />
                            )}
                            <span className="text-lg font-semibold">
                                {isUploading ? "Processing..." : "Upload Paper PDF"}
                            </span>
                        </div>
                        <p className="mt-4 text-sm text-gray-500">
                            Supports double-column PDFs. Max size 500MB.
                        </p>
                    </label>
                </div>
            </div>
        </div>
    );
};

export default Home;
