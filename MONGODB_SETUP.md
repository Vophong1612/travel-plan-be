# MongoDB Setup Guide

MongoDB is the recommended **on-premise alternative** to Firestore for the AI Travel Planner. This guide shows you how to set up and configure MongoDB.

## 🚀 Why MongoDB?

- **✅ On-premise**: Full control over your data
- **✅ No cloud dependencies**: Works completely offline
- **✅ Document-based**: Similar to Firestore's document model
- **✅ Mature ecosystem**: Excellent Python support and tooling
- **✅ Performance**: Optimized for your specific hardware

## 📦 Installation Options

### Option 1: Docker Compose (Recommended)

```bash
# Start MongoDB and Redis with the provided docker-compose.yml
docker-compose up -d

# Verify MongoDB is running
docker-compose logs mongodb

# Access MongoDB shell
docker exec -it travel-planner-mongodb mongosh
```

**What you get:**
- MongoDB 7.0 with authentication
- Redis for sessions
- Mongo Express (web UI) at `http://localhost:8081`
- Persistent data volumes

### Option 2: Native Installation

**Ubuntu/Debian:**
```bash
# Import MongoDB public key
curl -fsSL https://pgp.mongodb.com/server-7.0.asc | sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor

# Add MongoDB repository
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list

# Install MongoDB
sudo apt-get update
sudo apt-get install -y mongodb-org

# Start MongoDB
sudo systemctl start mongod
sudo systemctl enable mongod
```

**macOS:**
```bash
# Using Homebrew
brew tap mongodb/brew
brew install mongodb-community@7.0

# Start MongoDB
brew services start mongodb-community@7.0
```

**Windows:**
- Download MongoDB Community Server from [mongodb.com](https://www.mongodb.com/try/download/community)
- Run the installer with default settings
- MongoDB will start as a Windows service

## ⚙️ Configuration

### Environment Variables

Set these in your `.env` file:

```bash
# Enable MongoDB
USE_MONGODB=true

# MongoDB connection settings
MONGODB_HOST=localhost
MONGODB_PORT=27017
MONGODB_DATABASE=travel_planner

# Authentication (if enabled)
MONGODB_USERNAME=admin
MONGODB_PASSWORD=password123
MONGODB_AUTH_DATABASE=admin
```

### Authentication Setup (Optional but Recommended)

If you want to enable authentication:

```bash
# Connect to MongoDB shell
mongosh

# Switch to admin database
use admin

# Create admin user
db.createUser({
  user: "admin",
  pwd: "password123",
  roles: ["root"]
})

# Exit and restart MongoDB with authentication
exit
```

Then add these lines to `/etc/mongod.conf`:
```yaml
security:
  authorization: enabled
```

And restart MongoDB:
```bash
sudo systemctl restart mongod
```

## 📊 Database Structure

The AI Travel Planner uses these MongoDB collections:

- **`user_profiles`**: User preferences and profiles
- **`trips`**: Trip information and metadata
- **`itineraries`**: Daily itinerary details
- **`sessions`**: Temporary session data (handled by Redis)

## 🔧 Configuration Examples

### Development Setup

```bash
# .env for local development
USE_MONGODB=true
MONGODB_HOST=localhost
MONGODB_PORT=27017
MONGODB_DATABASE=travel_planner_dev
# No authentication for local dev
```

### Production Setup

```bash
# .env for production
USE_MONGODB=true
MONGODB_HOST=your-mongodb-server
MONGODB_PORT=27017
MONGODB_DATABASE=travel_planner_prod
MONGODB_USERNAME=travel_app_user
MONGODB_PASSWORD=secure_password_here
MONGODB_AUTH_DATABASE=travel_planner_prod
```

### Docker Compose Setup

```bash
# Use the provided docker-compose.yml
cp .env.template .env

# Edit .env:
USE_MONGODB=true
MONGODB_HOST=mongodb  # Docker service name
MONGODB_PORT=27017
MONGODB_DATABASE=travel_planner
MONGODB_USERNAME=admin
MONGODB_PASSWORD=password123
MONGODB_AUTH_DATABASE=admin

# Start services
docker-compose up -d
```

## 🧪 Testing the Setup

```bash
# Test MongoDB connection
python -c "
import asyncio
from src.database.mongodb_client import mongodb_client

async def test():
    health = await mongodb_client.health_check()
    print('MongoDB Health:', health)

asyncio.run(test())
"

# Test the application
python test_gemini_integration.py
python run_server.py --dev
```

## 🔍 Monitoring & Management

### MongoDB Shell Commands

```bash
# Connect to MongoDB
mongosh mongodb://admin:password123@localhost:27017/travel_planner

# List databases
show dbs

# Switch to travel planner database
use travel_planner

# List collections
show collections

# Count documents
db.user_profiles.countDocuments()
db.trips.countDocuments()

# Find recent trips
db.trips.find().sort({created_at: -1}).limit(5)
```

### Web Interface (Mongo Express)

If using Docker Compose, access the web UI at:
- **URL**: http://localhost:8081
- **Username**: admin
- **Password**: admin123

### Backup and Restore

```bash
# Backup database
mongodump --host localhost:27017 --db travel_planner --out backup/

# Restore database
mongorestore --host localhost:27017 --db travel_planner backup/travel_planner/
```

## 🚀 Performance Optimization

### Indexing

Create these indexes for better performance:

```javascript
// Connect to MongoDB shell
use travel_planner

// User profiles index
db.user_profiles.createIndex({"user_id": 1}, {"unique": true})

// Trips indexes
db.trips.createIndex({"trip_id": 1}, {"unique": true})
db.trips.createIndex({"user_id": 1, "created_at": -1})

// Itineraries index
db.itineraries.createIndex({"trip_id": 1, "day_number": 1}, {"unique": true})
```

### Memory Configuration

Add to `/etc/mongod.conf`:
```yaml
storage:
  wiredTiger:
    engineConfig:
      cacheSizeGB: 2  # Adjust based on available RAM
```

## 🔧 Troubleshooting

### Common Issues

**Connection refused:**
```bash
# Check if MongoDB is running
sudo systemctl status mongod

# Check logs
sudo journalctl -u mongod

# Restart if needed
sudo systemctl restart mongod
```

**Authentication failed:**
```bash
# Verify user exists
mongosh --eval "db.runCommand({usersInfo: 'admin'})"

# Reset password if needed
mongosh --eval "
use admin
db.changeUserPassword('admin', 'new_password')
"
```

**Python connection errors:**
```bash
# Install MongoDB drivers
pip install pymongo motor

# Test connection
python -c "
import pymongo
client = pymongo.MongoClient('mongodb://localhost:27017/')
print(client.server_info())
"
```

### Performance Issues

```bash
# Check database stats
mongosh --eval "db.stats()"

# Monitor operations
mongosh --eval "db.currentOp()"

# Check indexes
mongosh --eval "db.trips.getIndexes()"
```

## 🔄 Migration from Firestore

If you're migrating from Firestore to MongoDB:

1. **Export Firestore data**:
   ```bash
   gcloud firestore export gs://your-backup-bucket/firestore-backup
   ```

2. **Convert and import to MongoDB**:
   ```python
   # Use the migration script (create one based on your data structure)
   python scripts/migrate_firestore_to_mongodb.py
   ```

3. **Update configuration**:
   ```bash
   USE_MONGODB=true
   # Remove Firestore settings
   ```

4. **Test thoroughly** before switching production traffic

## 📚 Additional Resources

- [MongoDB Documentation](https://docs.mongodb.com/)
- [PyMongo Tutorial](https://pymongo.readthedocs.io/en/stable/tutorial.html)
- [Motor (Async) Documentation](https://motor.readthedocs.io/)
- [MongoDB Performance Best Practices](https://docs.mongodb.com/manual/administration/analyzing-mongodb-performance/)

---

**Need help?** Check the troubleshooting section or create an issue in the repository. 