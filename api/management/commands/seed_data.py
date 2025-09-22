from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from api.models import PhotoHunt, UserProfile

User = get_user_model()

class Command(BaseCommand):
    help = 'Seed the database with sample PhotoHunt data'

    def handle(self, *args, **options):
        self.stdout.write('🌱 Seeding database with sample data...')
        
        # Create a system user for sample data
        system_user, created = User.objects.get_or_create(
            email='system@photohunter.com',
            defaults={
                'name': 'System',
                'username': 'system@photohunter.com'
            }
        )
        
        if created:
            system_user.set_password('system123')
            system_user.save()
            UserProfile.objects.create(user=system_user)
            self.stdout.write('✅ Created system user')
        
        # Sample PhotoHunts from the React Native app
        sample_photohunts = [
            {
                'name': 'Sagrada Familia',
                'description': 'Capture the iconic basilica in all its architectural glory.',
                'latitude': 41.3907,
                'longitude': 2.1589,
                'reference_image': 'https://images.unsplash.com/photo-1539037116277-4db20889f2d4?w=800',
                'is_user_generated': False
            },
            {
                'name': 'Park Güell',
                'description': 'Find the colorful mosaic dragon and panoramic city views.',
                'latitude': 41.3835,
                'longitude': 2.1765,
                'reference_image': 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800',
                'is_user_generated': False
            },
            {
                'name': 'Casa Batlló',
                'description': 'Photograph Gaudí\'s masterpiece with its organic facade.',
                'latitude': 41.3942,
                'longitude': 2.1897,
                'reference_image': 'https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=800',
                'is_user_generated': False
            },
            {
                'name': 'Las Ramblas',
                'description': 'Capture the vibrant street life and historic boulevard.',
                'latitude': 41.3768,
                'longitude': 2.1614,
                'reference_image': 'https://images.unsplash.com/photo-1555993539-1732b0258235?w=800',
                'is_user_generated': False
            },
            {
                'name': 'Casa Milà',
                'description': 'Photograph the wavy stone facade and iron balconies.',
                'latitude': 41.3879,
                'longitude': 2.1682,
                'reference_image': 'https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=800',
                'is_user_generated': False
            },
            {
                'name': 'Tibidabo',
                'description': 'Get the best city view from Barcelona\'s highest point.',
                'latitude': 41.389,
                'longitude': 2.1821,
                'reference_image': 'https://images.unsplash.com/photo-1555993539-1732b0258235?w=800',
                'is_user_generated': False
            },
            {
                'name': 'Montjuïc Castle',
                'description': 'Capture the historic fortress overlooking the harbor.',
                'latitude': 41.3726,
                'longitude': 2.19,
                'reference_image': 'https://images.unsplash.com/photo-1555993539-1732b0258235?w=800',
                'is_user_generated': False
            },
            {
                'name': 'Arc de Triomf',
                'description': 'Photograph the red brick arch and palm-lined promenade.',
                'latitude': 41.3854,
                'longitude': 2.1477,
                'reference_image': 'https://images.unsplash.com/photo-1555993539-1732b0258235?w=800',
                'is_user_generated': False
            },
            {
                'name': 'Bunkers del Carmel',
                'description': 'Find the secret viewpoint with 360° city panorama.',
                'latitude': 41.3953,
                'longitude': 2.1711,
                'reference_image': 'https://images.unsplash.com/photo-1555993539-1732b0258235?w=800',
                'is_user_generated': False
            },
            {
                'name': 'Gothic Quarter',
                'description': 'Explore medieval streets and hidden courtyards.',
                'latitude': 41.3792,
                'longitude': 2.1555,
                'reference_image': 'https://images.unsplash.com/photo-1555993539-1732b0258235?w=800',
                'is_user_generated': False
            }
        ]
        
        created_count = 0
        for photohunt_data in sample_photohunts:
            photohunt, created = PhotoHunt.objects.get_or_create(
                name=photohunt_data['name'],
                defaults={
                    'description': photohunt_data['description'],
                    'latitude': photohunt_data['latitude'],
                    'longitude': photohunt_data['longitude'],
                    'reference_image': photohunt_data['reference_image'],
                    'created_by': system_user,
                    'is_user_generated': photohunt_data['is_user_generated']
                }
            )
            if created:
                created_count += 1
        
        self.stdout.write(f'✅ Created {created_count} sample PhotoHunts')
        self.stdout.write('🎉 Database seeding completed!')
