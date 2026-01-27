import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getProjects, deleteProject, updateProjectMetadata } from '../api';
import { FileText, Trash2, ExternalLink, ArrowLeft, Loader2, Edit2, Check, X } from 'lucide-react';

const ProjectsList = () => {
    const [projects, setProjects] = useState([]);
    const [loading, setLoading] = useState(true);
    const [deletingId, setDeletingId] = useState(null);
    const [editingId, setEditingId] = useState(null);
    const [editValue, setEditValue] = useState("");

    useEffect(() => {
        fetchProjects();
    }, []);

    const fetchProjects = async () => {
        try {
            const { data } = await getProjects();
            setProjects(data);
        } catch (error) {
            console.error("Failed to fetch projects", error);
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (id) => {
        if (!window.confirm("Are you sure you want to delete this project? All files will be permanently removed.")) {
            return;
        }

        setDeletingId(id);
        try {
            await deleteProject(id);
            setProjects(projects.filter(p => p.id !== id));
        } catch (error) {
            alert("Failed to delete project");
        } finally {
            setDeletingId(null);
        }
    };

    const startEditing = (project) => {
        setEditingId(project.id);
        setEditValue(project.original_filename || "");
    };

    const cancelEditing = () => {
        setEditingId(null);
        setEditValue("");
    };

    const saveEditing = async (id) => {
        if (!editValue.trim()) return;

        try {
            await updateProjectMetadata(id, { original_filename: editValue });
            setProjects(projects.map(p =>
                p.id === id ? { ...p, original_filename: editValue } : p
            ));
            setEditingId(null);
        } catch (error) {
            alert("Failed to rename project");
            console.error(error);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-screen">
                <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 p-8">
            <div className="max-w-4xl mx-auto">
                <div className="flex items-center gap-4 mb-8">
                    <Link to="/" className="p-2 hover:bg-gray-200 rounded-full transition-colors">
                        <ArrowLeft className="w-6 h-6 text-gray-600" />
                    </Link>
                    <h1 className="text-2xl font-bold text-gray-800">My Projects</h1>
                </div>

                <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                    {projects.length === 0 ? (
                        <div className="p-12 text-center text-gray-500">
                            <FileText className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                            <p>No projects found.</p>
                            <Link to="/" className="text-indigo-600 hover:underline mt-2 inline-block">
                                Create your first project
                            </Link>
                        </div>
                    ) : (
                        <table className="w-full text-left">
                            <thead className="bg-gray-50 border-b border-gray-100">
                                <tr>
                                    <th className="px-6 py-4 font-medium text-gray-500 text-sm">Project Name</th>
                                    <th className="px-6 py-4 font-medium text-gray-500 text-sm">Created At</th>
                                    <th className="px-6 py-4 font-medium text-gray-500 text-sm text-right">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100">
                                {projects.map((project) => (
                                    <tr key={project.id} className="hover:bg-gray-50 transition-colors">
                                        <td className="px-6 py-4">
                                            <div className="flex items-center gap-3">
                                                <div className="w-8 h-8 rounded bg-indigo-100 flex items-center justify-center text-indigo-600 shrink-0">
                                                    <FileText className="w-4 h-4" />
                                                </div>
                                                <div className="flex-1 min-w-0">
                                                    {editingId === project.id ? (
                                                        <div className="flex items-center gap-2">
                                                            <input
                                                                type="text"
                                                                className="border border-indigo-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 w-full"
                                                                value={editValue}
                                                                onChange={(e) => setEditValue(e.target.value)}
                                                                autoFocus
                                                            />
                                                            <button onClick={() => saveEditing(project.id)} className="text-green-600 hover:bg-green-50 p-1 rounded">
                                                                <Check className="w-4 h-4" />
                                                            </button>
                                                            <button onClick={cancelEditing} className="text-gray-500 hover:bg-gray-100 p-1 rounded">
                                                                <X className="w-4 h-4" />
                                                            </button>
                                                        </div>
                                                    ) : (
                                                        <div className="flex items-center gap-2 group">
                                                            <div className="font-medium text-gray-900 truncate max-w-[200px] sm:max-w-[300px]" title={project.original_filename}>
                                                                {project.original_filename || `Project ${project.id.slice(0, 8)}`}
                                                            </div>
                                                            <button
                                                                onClick={() => startEditing(project)}
                                                                className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-indigo-600 transition-opacity p-1"
                                                                title="Rename"
                                                            >
                                                                <Edit2 className="w-3 h-3" />
                                                            </button>
                                                        </div>
                                                    )}
                                                    <div className="text-xs text-gray-400 font-mono">
                                                        ID: {project.id.slice(0, 8)}
                                                    </div>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 text-sm text-gray-500 whitespace-nowrap">
                                            {new Date(project.created_at).toLocaleString()}
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            <div className="flex items-center justify-end gap-2">
                                                <Link
                                                    to={`/editor/${project.id}`}
                                                    className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-indigo-600 hover:bg-indigo-50 rounded-md transition-colors"
                                                >
                                                    <ExternalLink className="w-3.5 h-3.5" />
                                                    Open
                                                </Link>
                                                <button
                                                    onClick={() => handleDelete(project.id)}
                                                    disabled={deletingId === project.id}
                                                    className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 rounded-md transition-colors disabled:opacity-50"
                                                >
                                                    {deletingId === project.id ? (
                                                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                                    ) : (
                                                        <Trash2 className="w-3.5 h-3.5" />
                                                    )}
                                                    Delete
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            </div>
        </div>
    );
};

export default ProjectsList;
