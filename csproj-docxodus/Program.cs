using System;
using System.IO;
using Docxodus;
using DocumentFormat.OpenXml.Packaging;

class Program
{
    static int Main(string[] args)
    {
        // Parse arguments: <original> <modified> <output> [--author=<name>]
        if (args.Length < 3)
        {
            Console.WriteLine("Usage: redline <original.docx> <modified.docx> <output.docx> [--author=<name>]");
            return 1;
        }

        string originalFilePath = args[0];
        string modifiedFilePath = args[1];
        string outputFilePath = args[2];
        string authorTag = "Redline";

        // Parse optional --author flag
        for (int i = 3; i < args.Length; i++)
        {
            if (args[i].StartsWith("--author="))
            {
                authorTag = args[i].Substring("--author=".Length);
            }
        }

        if (!File.Exists(originalFilePath))
        {
            Console.Error.WriteLine($"Error: Original file does not exist: {originalFilePath}");
            return 1;
        }

        if (!File.Exists(modifiedFilePath))
        {
            Console.Error.WriteLine($"Error: Modified file does not exist: {modifiedFilePath}");
            return 1;
        }

        try
        {
            var originalBytes = File.ReadAllBytes(originalFilePath);
            var modifiedBytes = File.ReadAllBytes(modifiedFilePath);
            var originalDocument = new WmlDocument(originalFilePath, originalBytes);
            var modifiedDocument = new WmlDocument(modifiedFilePath, modifiedBytes);

            var comparisonSettings = new WmlComparerSettings
            {
                AuthorForRevisions = authorTag,
                DetailThreshold = 0
            };

            var comparisonResults = WmlComparer.Compare(originalDocument, modifiedDocument, comparisonSettings);
            var revisions = WmlComparer.GetRevisions(comparisonResults, comparisonSettings);

            // Output results
            Console.WriteLine($"Revisions found: {revisions.Count}");

            File.WriteAllBytes(outputFilePath, comparisonResults.DocumentByteArray);
            return 0;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"Error: {ex.Message}");
            Console.Error.WriteLine("Detailed Stack Trace:");
            Console.Error.WriteLine(ex.StackTrace);
            return 1;
        }
    }
}
