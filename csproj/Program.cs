using System;
using System.IO;
using OpenXmlPowerTools;
using DocumentFormat.OpenXml.Packaging;

class Program
{
    static void Main(string[] args)
    {
        if (args.Length != 4)
        {
            Console.WriteLine("Usage: redlines <author_tag> <original_path.docx> <modified_path.docx> <redline_path.docx>");
            return;
        }

        string authorTag = args[0];
        string originalFilePath = args[1];
        string modifiedFilePath = args[2];
        string outputFilePath = args[3];

        if (!File.Exists(originalFilePath) || !File.Exists(modifiedFilePath))
        {
            Console.WriteLine("Error: One or both files do not exist.");
            return;
        }

        try
        {
            var originalBytes = File.ReadAllBytes(originalFilePath);
            var modifiedBytes = File.ReadAllBytes(modifiedFilePath);
            var originalDocument = new WmlDocument(originalFilePath, originalBytes);
            Console.WriteLine(originalDocument);
            var modifiedDocument = new WmlDocument(modifiedFilePath, modifiedBytes);
            Console.WriteLine(modifiedDocument);
            var comparisonSettings = new WmlComparerSettings
            {
                AuthorForRevisions = authorTag,
                DetailThreshold = 0
            };

            var comparisonResults = WmlComparer.Compare(originalDocument, modifiedDocument, comparisonSettings);
            Console.WriteLine(comparisonResults);
            var revisions = WmlComparer.GetRevisions(comparisonResults, comparisonSettings);
            Console.WriteLine(revisions);

            // Output results
            Console.WriteLine($"Revisions found: {revisions.Count}");

            File.WriteAllBytes(outputFilePath, comparisonResults.DocumentByteArray);
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Error: {ex.Message}");
            Console.WriteLine("Detailed Stack Trace:");
            Console.WriteLine(ex.StackTrace);
        }
    }
}

