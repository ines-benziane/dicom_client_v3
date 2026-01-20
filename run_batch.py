import csv
import subprocess
import click

@click.command()
@click.option('--file', help='Chemin du CSV (Format: PatientID,SeriesDescription)')
def main(file):
    with open(file, mode='r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or len(row) < 2: continue
            
            p_id = row[0].strip()
            series_desc = row[1].strip()
            
            click.echo(click.style(f"\n Batch : ID {p_id} | Série {series_desc}", fg='blue', bold=True))
            
            cmd = [
                "python", "cli.py", "move",
                f"--patient-id={p_id}",
                "--level=SERIES",
                f"--series-description={series_desc}"
            ]
            
            try:
                subprocess.run(cmd, check=True)
            except subprocess.CalledProcessError:
                click.echo(click.style(f" Erreur critique sur PatientID: {p_id}", fg='red'))

if __name__ == "__main__":
    main()