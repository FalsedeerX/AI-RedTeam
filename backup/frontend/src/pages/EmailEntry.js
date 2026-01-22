function EmailEntry({ onVerify }) {
    const [email, setEmail] = React.useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        if (email.trim()) {
            // Call the onVerify callback to navigate to dashboard
            onVerify(email);
        }
    };

    return (
        <div className="min-h-screen bg-white flex items-center justify-center">
            <div className="max-w-md w-full mx-4 text-center">
                <h1 className="text-4xl font-bold text-black mb-8">
                    Protect your business with AI - enter your email to get started
                </h1>
                <form onSubmit={handleSubmit} className="space-y-6">
                    <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="Enter your email"
                        className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:outline-none focus:border-blue-500 text-black"
                        required
                    />
                    <button
                        type="submit"
                        className="w-full bg-blue-600 text-white font-semibold py-3 rounded-lg hover:bg-blue-700 transition-colors"
                    >
                        Verify
                    </button>
                </form>
            </div>
        </div>
    );
}

