import axios from 'axios';

class PlaylistManager {
    constructor() {
        this.apiUrl = "http://localhost:8000/api/songs/";
        this.songs = [];
        this.currentIndex = 0;
        this.filters = {
            artist: null,
            album: null,
        };
        this.loadSongs();
    }

    async loadSongs() {
        try {
            const response = await axios.get(this.apiUrl);
            this.songs = response.data;
        } catch (error) {
            console.error("Error loading songs:", error);
        }

        return this.songs;
    }

    async refresh() {
        try {
            const response = await axios.get(this.apiUrl, {
                params: this.filters,
            });
            this.songs = response.data;
        } catch (error) {
            console.error("Error refreshing songs:", error);
        }

        return this.songs;
    }

    filter({ artist = null, album = null }) {
        this.filters.artist = artist;
        this.filters.album = album;
        this.refresh();
    }

    setCurrentSong(songId) {
        const newIndex = this.songs.findIndex((song) => song.id === songId);
        
        this.currentIndex = newIndex;
    }

    getCurrentSong() {
        if (this.songs.length === 0) return null;
        return this.songs[this.currentIndex];
    }

    next() {
        if (this.songs.length === 0) return;
        this.currentIndex = (this.currentIndex + 1) % this.songs.length;
    }

    prev() {
        if (this.songs.length === 0) return;
        this.currentIndex = (this.currentIndex - 1 + this.songs.length) % this.songs.length;
    }

    shuffle() {
        for (let i = this.songs.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [this.songs[i], this.songs[j]] = [this.songs[j], this.songs[i]];
        }
        this.currentIndex = 0; // Reset to start after shuffle
    }

    async addSong(songData) {
        try {
            const response = await axios.post(this.apiUrl, songData);
            this.songs.push(response.data);
        } catch (error) {
            console.error("Error adding song:", error);
        }
    }
}

export default PlaylistManager;