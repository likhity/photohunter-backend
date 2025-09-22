from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from api.models import PhotoHunt, UserProfile
import json
import os
from pathlib import Path

User = get_user_model()

class Command(BaseCommand):
    help = 'Import PhotoHunts from the React Native app JSON file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='../photo-hunter-app/data/photohunts.json',
            help='Path to the photohunts.json file'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing PhotoHunts before importing'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        
        # If relative path, make it relative to the backend directory
        if not os.path.isabs(file_path):
            backend_dir = Path(__file__).parent.parent.parent.parent
            file_path = backend_dir / file_path
        
        if not os.path.exists(file_path):
            self.stdout.write(
                self.style.ERROR(f'File not found: {file_path}')
            )
            return
        
        # Clear existing PhotoHunts if requested
        if options['clear']:
            count = PhotoHunt.objects.count()
            PhotoHunt.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(f'Cleared {count} existing PhotoHunts')
            )
        
        # Create or get system user
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
        
        # Load JSON data
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                photohunts_data = json.load(f)
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error reading JSON file: {e}')
            )
            return
        
        # Import PhotoHunts
        imported_count = 0
        skipped_count = 0
        
        for photohunt_data in photohunts_data:
            # Check if PhotoHunt already exists (by name and coordinates)
            existing = PhotoHunt.objects.filter(
                name=photohunt_data['name'],
                latitude=photohunt_data['lat'],
                longitude=photohunt_data['long']
            ).first()
            
            if existing:
                self.stdout.write(
                    f'⏭️  Skipped existing: {photohunt_data["name"]}'
                )
                skipped_count += 1
                continue
            
            # Create new PhotoHunt
            try:
                photohunt = PhotoHunt.objects.create(
                    name=photohunt_data['name'],
                    description=photohunt_data['description'],
                    latitude=photohunt_data['lat'],
                    longitude=photohunt_data['long'],
                    reference_image=photohunt_data.get('referenceImage'),
                    created_by=system_user,
                    is_user_generated=photohunt_data.get('isUserGenerated', False),
                    is_active=True
                )
                
                self.stdout.write(
                    f'✅ Imported: {photohunt.name}'
                )
                imported_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'❌ Error importing {photohunt_data["name"]}: {e}'
                    )
                )
        
        # Update system user stats
        profile, created = UserProfile.objects.get_or_create(user=system_user)
        profile.total_created = PhotoHunt.objects.filter(created_by=system_user).count()
        profile.save()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n🎉 Import completed!\n'
                f'   Imported: {imported_count} PhotoHunts\n'
                f'   Skipped: {skipped_count} existing PhotoHunts\n'
                f'   Total in database: {PhotoHunt.objects.count()} PhotoHunts'
            )
        )
