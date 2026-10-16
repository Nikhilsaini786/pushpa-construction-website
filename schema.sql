CREATE DATABASE IF NOT EXISTS construction_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE construction_db;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(190) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'customer',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(160) NOT NULL,
    category VARCHAR(80) NOT NULL,
    description TEXT NOT NULL,
    image_url VARCHAR(500) DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS enquiries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(190) NOT NULL,
    phone VARCHAR(30) NOT NULL,
    project_type VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO projects (title, category, description, image_url)
SELECT '3-Storey Luxury Villa', 'Residential', 'Premium modern 3-storey independent luxury residence built with RCC framing, decorative CNC jali elevation, powder-coated designer boundary gate, and elegant exterior lighting in Jaipur, Rajasthan.',
'/static/image/project-1.jpg'
WHERE NOT EXISTS (SELECT 1 FROM projects WHERE title='3-Storey Luxury Villa');

INSERT INTO projects (title, category, description, image_url)
SELECT 'Royal Blue Contemporary Duplex', 'Residential', 'Architectural masterpiece featuring contemporary duplex facade in royal blue accents, false ceiling with warm recessed LED lighting, custom brass heritage gates, and premium finish in Jaipur.',
'/static/image/project-2.jpg'
WHERE NOT EXISTS (SELECT 1 FROM projects WHERE title='Royal Blue Contemporary Duplex');

INSERT INTO projects (title, category, description, image_url)
SELECT 'Modern Designer Residence', 'Residential', 'Complete turnkey residential project including structural design, custom boundary elevation with designer wall sconces, modern window joinery, and durable weather-proof exterior finish.',
'/static/image/project-3.jpg'
WHERE NOT EXISTS (SELECT 1 FROM projects WHERE title='Modern Designer Residence');

INSERT INTO projects (title, category, description, image_url)
SELECT 'Commercial Complex & Showroom', 'Commercial', 'Multi-storey commercial shopping complex and showroom space featuring modern architecture, spacious floor plans, and robust structural engineering in Rajasthan.',
'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1200&q=80'
WHERE NOT EXISTS (SELECT 1 FROM projects WHERE title='Commercial Complex & Showroom');

INSERT INTO projects (title, category, description, image_url)
SELECT 'Corporate Office Tower', 'Commercial', 'State-of-the-art office infrastructure with advanced earthquake-resistant construction, energy-efficient architecture, and modern civil engineering.',
'https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=1200&q=80'
WHERE NOT EXISTS (SELECT 1 FROM projects WHERE title='Corporate Office Tower');

INSERT INTO projects (title, category, description, image_url)
SELECT 'Civil Infrastructure & Roadwork', 'Infrastructure', 'Public and private civil infrastructure development including concrete roads, drainage networks, and commercial site preparation across Rajasthan.',
'https://images.unsplash.com/photo-1519501025264-65ba15a82390?auto=format&fit=crop&w=1200&q=80'
WHERE NOT EXISTS (SELECT 1 FROM projects WHERE title='Civil Infrastructure & Roadwork');

