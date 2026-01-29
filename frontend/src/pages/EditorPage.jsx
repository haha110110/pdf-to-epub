import React, { useEffect, useState, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { getContent, saveContent, getStatus, buildEpub, getDownloadUrl, getDocxDownloadUrl, getSourcePackageUrl } from '../api';
import EditorWrapper from '../components/EditorWrapper';
import { Save, Download, FileDown, BookOpen, Loader2, ArrowLeft, FileText } from 'lucide-react';
import { Link } from 'react-router-dom';

const EditorPage = () => {
    const { projectId } = useParams();
    const [content, setContent] = useState('');
    const [status, setStatus] = useState('loading'); // loading, ready, saving, building
    const [downloadLink, setDownloadLink] = useState(null);
    const editorRef = useRef(null);

    useEffect(() => {
        loadContent();
    }, [projectId]);

    const loadContent = async () => {
        try {
            // Poll status first
            // In a real app we'd poll until 'ready'
            const { data: statusData } = await getStatus(projectId);
            if (statusData.status === 'processing') {
                setTimeout(loadContent, 2000);
                return;
            }

            const { data } = await getContent(projectId);
            setContent(data.content);
            setStatus('ready');
        } catch (error) {
            console.error("Failed to load content", error);
            setStatus('error');
        }
    };

    const handleSave = async () => {
        if (!editorRef.current) return;
        const currentMarkdown = editorRef.current.getInstance().getMarkdown();

        setStatus('saving');
        try {
            await saveContent(projectId, currentMarkdown);
            setStatus('ready');
        } catch (error) {
            console.error("Save failed", error);
            setStatus('error');
        }
    };

    const handleBuild = async () => {
        // First save
        await handleSave();

        setStatus('building');
        try {
            // Trigger build
            await buildEpub(projectId);
            // For now, assume sync or quick build. In real app, poll status.
            // But we implemented a simple blocking call or file check in v1 plan?
            // Actually backend build trigger doesn't wait? 
            // The API I wrote `POST /build` wasn't fully detailed in routes.py yet!
            // I need to double check routes.py.
            // Wait, I didn't write the `/build` endpoint in routes.py yet! 
            // I missed it in step 68!

            // I will implement the UI assuming it exists, and then go fix the backend.
            setDownloadLink(getDownloadUrl(projectId));
            setStatus('ready');
        } catch (error) {
            console.error("Build failed", error);
            setStatus('error'); // Show error
        }
    };

    if (status === 'loading') {
        return (
            <div className="flex flex-col items-center justify-center h-screen">
                <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
                <p className="mt-4 text-gray-500">Processing PDF... This may take a minute.</p>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-screen bg-white">
            {/* Header */}
            <header className="flex items-center justify-between px-6 py-4 border-b bg-white z-10">
                <div className="flex items-center gap-4">
                    <Link to="/" className="p-2 hover:bg-gray-100 rounded-full">
                        <ArrowLeft className="w-5 h-5" />
                    </Link>
                    <h1 className="text-xl font-bold text-gray-800">Editor Workspace</h1>
                    <span className="px-2 py-1 text-xs font-mono bg-gray-100 rounded text-gray-500">
                        {projectId.slice(0, 8)}...
                    </span>
                </div>

                <div className="flex items-center gap-3">
                    {downloadLink && (
                        <a
                            href={downloadLink}
                            className="flex items-center gap-2 px-4 py-2 text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100"
                        >
                            <Download className="w-4 h-4" />
                            EPUB
                        </a>
                    )}

                    <a
                        href={getDocxDownloadUrl(projectId)}
                        className="flex items-center gap-2 px-4 py-2 text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100"
                        title="Download as Word Document"
                    >
                        <FileText className="w-4 h-4" />
                        Word
                    </a>

                    <a
                        href={getSourcePackageUrl(projectId)}
                        target="_blank"
                        rel="noreferrer"
                        className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
                        title="Download source files for offline editing"
                    >
                        <FileDown className="w-4 h-4" />
                        Source
                    </a>

                    <button
                        onClick={handleSave}
                        disabled={status === 'saving'}
                        className="flex items-center gap-2 px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
                    >
                        {status === 'saving' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                        Save
                    </button>

                    <button
                        onClick={handleBuild}
                        disabled={status === 'building'}
                        className="flex items-center gap-2 px-6 py-2 text-white bg-indigo-600 rounded-lg hover:bg-indigo-500 shadow-sm"
                    >
                        {status === 'building' ? <Loader2 className="w-4 h-4 animate-spin" /> : <BookOpen className="w-4 h-4" />}
                        Build EPUB
                    </button>
                </div>
            </header>

            {/* Editor Area */}
            <div className="flex-1 overflow-hidden relative">
                <EditorWrapper
                    ref={editorRef}
                    initialValue={content}
                />
            </div>
        </div>
    );
};

export default EditorPage;
