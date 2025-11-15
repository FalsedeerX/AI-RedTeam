function Dashboard({ userEmail }) {
    const [scanType, setScanType] = React.useState({
        ipRange: false,
        websiteUrl: false,
        githubRepo: false
    });
    const [inputValue, setInputValue] = React.useState('');

    const handleScanTypeChange = (type) => {
        setScanType(prev => ({
            ...prev,
            [type]: !prev[type]
        }));
    };

    const handleAttack = () => {
        // Handle attack button click
        console.log('Attack clicked with:', inputValue, scanType);
    };

    // Extract username from email (or use a default)
    const username = userEmail ? userEmail.split('@')[0] : 'User123';

    return (
        <div className="min-h-screen bg-white">
            <div className="container mx-auto px-8 py-12">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-start">
                    {/* Left Side */}
                    <div className="space-y-6">
                        <h1 className="text-5xl font-bold text-black">
                            Welcome, {username}
                        </h1>
                        <p className="text-lg text-black leading-relaxed">
                            Thank you for joining us on a journey to empower people all across the globe to secure their websites and software: its a pleasure to have you.
                        </p>
                    </div>

                    {/* Right Side */}
                    <div className="space-y-6">
                        <h2 className="text-2xl font-semibold text-black">
                            Select scan type (what input you will be providing)
                        </h2>
                        
                        <div className="space-y-4">
                            <label className="flex items-center space-x-3 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={scanType.ipRange}
                                    onChange={() => handleScanTypeChange('ipRange')}
                                    className="w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                                />
                                <span className="text-lg text-black">IP Range</span>
                            </label>
                            
                            <label className="flex items-center space-x-3 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={scanType.websiteUrl}
                                    onChange={() => handleScanTypeChange('websiteUrl')}
                                    className="w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                                />
                                <span className="text-lg text-black">Website URL</span>
                            </label>
                            
                            <label className="flex items-center space-x-3 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={scanType.githubRepo}
                                    onChange={() => handleScanTypeChange('githubRepo')}
                                    className="w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                                />
                                <span className="text-lg text-black">GitHub Repo</span>
                            </label>
                        </div>
                    </div>
                </div>

                {/* Input and Attack Button Section */}
                <div className="mt-12 relative">
                    {/* Decorative green line from left */}
                    <div className="absolute left-0 top-0 w-1/3 h-1 bg-green-500 transform -translate-y-1/2">
                        <div className="absolute right-0 top-1/2 transform -translate-y-1/2 translate-x-1/2">
                            <svg className="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd" />
                            </svg>
                        </div>
                    </div>

                    <div className="flex items-center space-x-4 max-w-4xl">
                        <input
                            type="text"
                            value={inputValue}
                            onChange={(e) => setInputValue(e.target.value)}
                            placeholder="Ex. http://example.com/"
                            className="flex-1 px-4 py-3 border-2 border-gray-300 rounded-lg focus:outline-none focus:border-blue-500 text-black"
                        />
                        <button
                            onClick={handleAttack}
                            className="bg-blue-600 text-white font-bold py-3 px-8 rounded-lg hover:bg-blue-700 transition-colors uppercase tracking-wide"
                        >
                            ATTACK
                        </button>
                    </div>

                    {/* Decorative green line from attack button */}
                    <div className="absolute right-0 top-0 w-1/4 h-1 bg-green-500 transform translate-y-1/2 rotate-12 origin-right">
                        <div className="absolute right-0 top-1/2 transform -translate-y-1/2 translate-x-1/2">
                            <svg className="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd" />
                            </svg>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

